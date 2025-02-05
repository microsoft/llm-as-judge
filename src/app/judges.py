"""
judges.py

This module implements:
  - A SuperJudge that is also a Judge (extends JudgeBase), orchestrating sub-judges.
  - A Mediator-like pattern: SuperJudge collects notifications from sub-judges.
  - A Plan used by the SuperJudge to evaluate each sub-judge's output in a structured way.
  - A Factory (JudgeFactory) that builds sub-judges from a Pydantic Assembly.
  - An Orchestrator (JudgeOrchestrator) that merges the SuperJudge + JudgeFactory logic into a
    single evaluation procedure.

Classes:
    JudgeBase: Abstract base for a judge that can evaluate a prompt.
    ConcreteJudge: A judge that is a ChatCompletionAgent for LLM interactions.
    SuperJudge: Extends JudgeBase, orchestrates multiple sub-judges, collects outputs, and
                can itself be considered a "judge" with a final verdict.
    JudgeEvaluationPlan: A Plan describing how the SuperJudge calls each sub-judge's evaluate().
    JudgeFactory: Builds sub-judges from an Assembly. Optionally also builds or configures a Kernel.
    JudgeOrchestrator: High-level class that uses the Factory + SuperJudge to produce a final verdict.

Usage:
    # 1) Create or load an Assembly (with .judges).
    # 2) Call JudgeOrchestrator.run_evaluation(assembly, prompt).
    #    -> Returns the final verdict from the SuperJudge after orchestrating sub-judges.
"""

import asyncio
import json
import os
from abc import ABC, abstractmethod
from typing import Any, List, Optional

import semantic_kernel as sk
from azure.cosmos import exceptions
from azure.cosmos.aio import CosmosClient
from azure.identity.aio import DefaultAzureCredential
from semantic_kernel.agents.chat_completion.chat_completion_agent import ChatCompletionAgent
from semantic_kernel.connectors.ai import FunctionChoiceBehavior
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.function_call_content import FunctionCallContent
from semantic_kernel.contents.function_result_content import FunctionResultContent
from semantic_kernel.functions.kernel_arguments import KernelArguments

# If you use SK planners, e.g., Plan
from semantic_kernel.planners.plan import Plan

# Import your Pydantic models
from app.schemas import Assembly, Judge

COSMOS_DB_NAME = os.getenv("COSMOS_DB_NAME", "mydb")
COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT", "https://myendpoint.documents.azure.com:443/")
COSMOS_ASSEMBLY_TABLE = os.getenv("COSMOS_ASSEMBLY_TABLE", "assemblies")


# =============================================================================
# 1. The MEdiator, which implements the notify method
# =============================================================================


class Mediator(ABC):
    """
    The Mediator interface declares the notify method used by judges (agents)
    to report events or results. Any concrete mediator (such as SuperJudge)
    must implement this method.
    """

    @abstractmethod
    def notify(self, sender: object, event: str, data: dict) -> None:
        """
        Notifies the mediator of an event that has occurred.

        :param sender: The judge sending the notification.
        :param event: A string describing the event type (e.g., "evaluation_done").
        :param data: A dictionary containing additional data (e.g., judge_id, result).
        """
        pass


# =============================================================================
# 2. Abstract Judge
# =============================================================================


class JudgeBase(ABC):
    """
    Abstract base for a judge that can evaluate a prompt.
    """

    def __init__(self) -> None:
        """
        Initialize the judge with no mediator reference.
        """
        self.mediator: Optional["Mediator"] = None

    @abstractmethod
    async def evaluate(self, prompt: str) -> None:
        """
        Evaluate a prompt asynchronously.
        """
        pass


# =============================================================================
# 3. Concrete Judge (Agent)
# =============================================================================


class ConcreteJudge(JudgeBase):
    """
    A judge that uses a ChatCompletionAgent to evaluate a prompt.
    Each instance references a shared Kernel but instantiates its own Agent in `evaluate()`.
    """

    def __init__(self, judge_data: Judge, kernel: sk.Kernel) -> None:
        super().__init__()
        self.judge_data = judge_data
        self.kernel = kernel

    async def evaluate(self, prompt: str) -> None:
        """
        Use ChatCompletionAgent to evaluate the prompt. Once done,
        notify the mediator with the result.
        """
        # 1) Parse the metaprompt
        try:
            meta = json.loads(self.judge_data.metaprompt)  # e.g. {"text": "..."}
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in metaprompt: {str(e)}") from e

        system_text = meta.get("text", "System Prompt Missing")

        # 2) Retrieve execution settings from the kernel (or fallback to "default")
        settings = self.kernel.get_prompt_execution_settings_from_service_id(
            service_id=str(self.judge_data.model)
        )
        if not settings:
            settings = self.kernel.get_prompt_execution_settings_from_service_id("default")

        settings.function_choice_behavior = FunctionChoiceBehavior.Auto()

        # 3) Build the agent
        agent = ChatCompletionAgent(
            service_id=str(self.judge_data.model) or "default",
            kernel=self.kernel,
            name=self.judge_data.name,
            instructions=system_text,
            arguments=KernelArguments(settings=settings),
        )

        # 4) Chat conversation
        chat_history = ChatHistory()
        chat_history.add_user_message(prompt)

        final_content = []
        async for msg_content in agent.invoke(chat_history):
            # Filter function calls (if not needed)
            if any(
                isinstance(item, (FunctionCallContent, FunctionResultContent))
                for item in msg_content.items
            ):
                continue
            if msg_content.content.strip():
                final_content.append(msg_content.content)

        result_str = "\n".join(final_content).strip() or "[No output from LLM]"

        if self.mediator:
            self.mediator.notify(
                sender=self,
                event="evaluation_done",
                data={
                    "judge_id": self.judge_data.id,
                    "judge_name": self.judge_data.name,
                    "result": result_str,
                },
            )


# =============================================================================
# 4. SuperJudge (also a Judge, plus Mediator-like behavior)
# =============================================================================


class SuperJudge(JudgeBase, Mediator):
    """
    A "judge of judges." This class:
      - Inherits from JudgeBase (so it's also a judge).
      - Orchestrates sub-judges (Mediator-like).
      - Collects their outputs in a final verdict.
      - Shares the kernel as needed if it wants to do any final summary or evaluation.

    You can override evaluate() to define how it runs sub-judges in parallel or in a plan.
    """

    def __init__(self, kernel: sk.Kernel, name: str = "SuperJudge") -> None:
        super().__init__()
        self.kernel = kernel
        self.name = name
        self._judges: List[JudgeBase] = []
        self._evaluations: List[dict] = []

    def register_judge(self, judge: JudgeBase) -> None:
        """
        Register a sub-judge for orchestration.
        """
        self._judges.append(judge)
        judge.mediator = self  # so sub-judges can notify us

    def notify(self, sender: object, event: str, data: dict) -> None:
        """
        Called by sub-judges upon completion of their evaluation.
        """
        if event == "evaluation_done":
            self._evaluations.append(data)

    def final_verdict(self) -> str:
        """
        Combine sub-judges' evaluations.
        """
        if not self._evaluations:
            return "[No evaluations received]"
        lines = []
        for ev in self._evaluations:
            lines.append(f"{ev['judge_name']} => {ev['result']}")
        return "\n".join(lines)

    async def evaluate(self, prompt: str) -> None:
        """
        Because SuperJudge is also a Judge, we can define an evaluation flow:
          - We can run sub-judges in parallel or in a plan.
          - Then we might do a final step using self.kernel if we want.
        """
        # For demonstration, we'll define a Plan that runs each sub-judge's evaluation
        plan = JudgeEvaluationPlan(super_judge=self, prompt=prompt)
        await plan.run_plan()


# =============================================================================
# 4. A Plan for the SuperJudge
# =============================================================================


class JudgeEvaluationPlan(Plan):
    """
    A semantic-kernel Plan describing how the SuperJudge calls each sub-judge.
    Could contain complex logic (sequential, parallel, branching, etc.).
    For simplicity, we'll run them in parallel.
    """

    def __init__(self, super_judge: SuperJudge, prompt: str):
        super().__init__(
            name="JudgeEvaluationPlan", description="Plan for orchestrating sub-judges."
        )
        self.super_judge = super_judge
        self.prompt = prompt

    async def run_plan(self) -> Any:
        """
        Execute the plan:
         - Evaluate all sub-judges in parallel
         - Return final verdict
        """
        # 1) Run all sub-judges in parallel
        await asyncio.gather(*(j.evaluate(self.prompt) for j in self.super_judge._judges))

        # 2) (Optionally) SuperJudge can do a final summary with self.super_judge.kernel
        # if desired. For now, we skip it.

        # 3) Return final verdict
        return self.super_judge.final_verdict()


# =============================================================================
# 5. Factory
# =============================================================================


class JudgeFactory:
    """
    Builds a kernel (optional) and produces sub-judges.
    Does NOT instantiate the "SuperJudge," but you may do so here if desired.

    Each judge is an agent that references the shared kernel.
    """

    @staticmethod
    def build_kernel() -> sk.Kernel:
        """
        Build a shared Kernel that sub-judges will reference.
        Add your AI services, plugins, etc.
        """
        kernel = sk.Kernel()
        return kernel

    @staticmethod
    def create_judges(assembly: Assembly, kernel: sk.Kernel) -> List[ConcreteJudge]:
        """
        Produce a list of ConcreteJudge objects from Pydantic Judge models.
        Each judge uses the provided kernel for its ChatCompletionAgent.
        """
        return [ConcreteJudge(judge_data=jd, kernel=kernel) for jd in assembly.judges]


# =============================================================================
# 6. Orchestration Class (Merges SuperJudge + Factory in a single procedure)
# =============================================================================


class JudgeOrchestrator:
    """
    A high-level class that merges the SuperJudge and JudgeFactory in one evaluation procedure.
    - You give it an Assembly (list of Pydantic Judge entries).
    - It builds a kernel, a SuperJudge, sub-judges, and orchestrates an evaluation.
    """

    @staticmethod
    async def run_evaluation(assembly: Assembly, prompt: str) -> str:
        """
        1) Build a shared kernel
        2) Instantiate a SuperJudge referencing that kernel
        3) Create sub-judges via JudgeFactory
        4) Register them in the SuperJudge
        5) Let the SuperJudge evaluate (which calls sub-judges in a plan)
        6) Return the final verdict
        """
        # 1) Shared kernel
        kernel = JudgeFactory.build_kernel()

        # 2) SuperJudge
        super_judge = SuperJudge(kernel=kernel, name=f"SuperJudge_{assembly.id}")

        # 3) Create sub-judges from the assembly
        sub_judges = JudgeFactory.create_judges(assembly, kernel=kernel)

        # 4) Register them
        for j in sub_judges:
            super_judge.register_judge(j)

        # 5) Evaluate
        await super_judge.evaluate(prompt)

        # 6) Final verdict
        return super_judge.final_verdict()


async def fetch_assembly(assembly_id: str) -> dict | None:
    """
    Helper function to fetch an Assembly document from Cosmos DB by its ID.
    Returns the document as a dict, or None if not found.
    """
    async with CosmosClient(COSMOS_ENDPOINT, DefaultAzureCredential()) as client:
        try:
            database = client.get_database_client(COSMOS_DB_NAME)
            # Confirm the database exists.
            await database.read()
        except exceptions.CosmosResourceNotFoundError:
            return None

        container = database.get_container_client(COSMOS_ASSEMBLY_TABLE)
        try:
            item = await container.read_item(item=assembly_id, partition_key=assembly_id)
            return item
        except exceptions.CosmosResourceNotFoundError:
            return None
