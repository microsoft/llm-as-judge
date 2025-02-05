from unittest.mock import AsyncMock, MagicMock

import pytest
import semantic_kernel as sk

from app.judges import (
    ConcreteJudge,
    JudgeBase,
    JudgeFactory,
    JudgeOrchestrator,
    Mediator,
    SuperJudge,
    fetch_assembly,
)
from app.schemas import Assembly, Judge


@pytest.mark.asyncio
async def test_concrete_judge_evaluate():
    # Mock Judge and Kernel
    judge_data = Judge(id="1", name="Judge1", model="https://example.com/model1", metaprompt='{"text": "Test Prompt"}')
    kernel = MagicMock(spec=sk.Kernel)
    kernel.get_prompt_execution_settings_from_service_id.return_value = MagicMock()

    # Create ConcreteJudge instance
    judge = ConcreteJudge(judge_data=judge_data, kernel=kernel)

    # Mock ChatCompletionAgent and its behavior
    agent_mock = AsyncMock()
    agent_mock.invoke.return_value = [MagicMock(content="Test Result")]
    ChatCompletionAgent = MagicMock(return_value=agent_mock)

    # Set mediator to capture notifications
    mediator_mock = MagicMock(spec=Mediator)
    judge.mediator = mediator_mock

    # Run evaluate
    await judge.evaluate("Test Prompt")

    # Assertions
    mediator_mock.notify.assert_called_once_with(
        sender=judge,
        event="evaluation_done",
        data={"judge_id": "1", "judge_name": "Judge1", "result": "Test Result"},
    )


@pytest.mark.asyncio
async def test_super_judge_evaluate():
    # Mock Kernel
    kernel = MagicMock(spec=sk.Kernel)

    # Create SuperJudge instance
    super_judge = SuperJudge(kernel=kernel)

    # Mock sub-judges
    sub_judge_mock = AsyncMock(spec=JudgeBase)
    sub_judge_mock.evaluate.return_value = None
    super_judge.register_judge(sub_judge_mock)

    # Run evaluate
    await super_judge.evaluate("Test Prompt")

    # Assertions
    sub_judge_mock.evaluate.assert_called_once_with("Test Prompt")


@pytest.mark.asyncio
async def test_judge_orchestrator_run_evaluation():
    # Mock Assembly and Kernel
    assembly = Assembly(
        id="assembly1",
        judges=[Judge(id="1", name="Judge1", model="https://example.com/model1", metaprompt='{"text": "Test Prompt"}')],
        roles=["role1", "role2"],
    )
    kernel = MagicMock(spec=sk.Kernel)
    JudgeFactory.build_kernel = MagicMock(return_value=kernel)

    # Mock SuperJudge and its methods
    super_judge_mock = AsyncMock(spec=SuperJudge)
    super_judge_mock.final_verdict.return_value = "Final Verdict"
    SuperJudge = MagicMock(return_value=super_judge_mock)

    # Run evaluation
    verdict = await JudgeOrchestrator.run_evaluation(assembly, "Test Prompt")

    # Assertions
    assert verdict == "Final Verdict"
    super_judge_mock.evaluate.assert_called_once_with("Test Prompt")


@pytest.mark.asyncio
async def test_fetch_assembly():
    # Mock CosmosClient and its behavior
    cosmos_client_mock = AsyncMock()
    cosmos_client_mock.get_database_client.return_value.get_container_client.return_value.read_item.return_value = {
        "id": "assembly1"
    }
    CosmosClient = MagicMock(return_value=cosmos_client_mock)

    # Run fetch_assembly
    assembly = await fetch_assembly("assembly1")

    # Assertions
    assert assembly == {"id": "assembly1"}
