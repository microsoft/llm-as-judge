"""
The configuration for the mailing service.
"""

import csv
import logging
import os
from typing import Optional

from azure.cosmos import exceptions
from azure.cosmos.aio import CosmosClient
from azure.identity.aio import DefaultAzureCredential
from dotenv import find_dotenv, load_dotenv
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app import __app__, __version__
from app.judges import JudgeOrchestrator, fetch_assembly
from app.schemas import RESPONSES, Assembly, ErrorMessage, Judge, JudgeEvaluation, SuccessMessage

load_dotenv(find_dotenv())

BLOB_CONN = os.getenv("BLOB_CONNECTION_STRING", "")
MODEL_URL: str = os.environ.get("GPT4_URL", "")
MODEL_KEY: str = os.environ.get("GPT4_KEY", "")
MONITOR: str = os.environ.get("AZ_CONNECTION_LOG", "")
COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT", "")

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


tags_metadata: list[dict] = [
    {
        "name": "Clients",
        "description": """
        Endpoints for managing clients.
        """,
    },
    {
        "name": "Emails",
        "description": """
        Endpoints to manage e-mail templates.
        """,
    },
    {
        "name": "Campaigns",
        "description": """
        Endpoints to Manage Campaigns.
        """,
    },
]

description: str = """
    Web API to manage transcription evaluation jobs from a Call Center.\n
    Leveraging Azure OpenAI, this engine provides interfaces and engines for evaluating transcriptions against
    aghnostic criterias. It also provides interfaces for improving existing transcriptions.
"""


app: FastAPI = FastAPI(
    title=__app__,
    version=__version__,
    description=description,
    openapi_tags=tags_metadata,
    openapi_url="/api/v1/openapi.json",
    responses=RESPONSES,  # type: ignore
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError  # pylint: disable=unused-argument
) -> JSONResponse:
    """
    validation_exception_handler Exception handler for validations.

    Args:
        request (Request): the request from the api
        exc (RequestValidationError): the validation raised by the process

    Returns:
        JSONResponse: A json encoded response with the validation errors.
    """

    response_body: ErrorMessage = ErrorMessage(
        success=False,
        type="Validation Error",
        title="Your request parameters didn't validate.",
        detail={"invalid-params": list(exc.errors())},
    )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=jsonable_encoder(response_body),
    )


@app.exception_handler(ResponseValidationError)
async def response_exception_handler(
    request: Request, exc: ResponseValidationError  # pylint: disable=unused-argument
) -> JSONResponse:
    """
    response_exception_handler Exception handler for response validations.

    Args:
        request (Request): the request from the api
        exc (RequestValidationError): the validation raised by the process

    Returns:
        JSONResponse: A json encoded response with the validation errors.
    """

    response_body: ErrorMessage = ErrorMessage(
        success=False,
        type="Response Error",
        title="Found Errors on processing your requests.",
        detail={"invalid-params": list(exc.errors())},
    )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=jsonable_encoder(response_body),
    )


@app.get("/list-judges", tags=["Judges"])
async def list_judges(name: Optional[str] = None, email: Optional[str] = None) -> JSONResponse:
    """ """
    async with CosmosClient(COSMOS_ENDPOINT, DefaultAzureCredential()) as client:
        try:
            database = client.get_database_client(os.getenv("COSMOS_DB_NAME", ""))
            database.read()
        except exceptions.CosmosResourceNotFoundError:
            client.create_database(os.getenv("COSMOS_DB_NAME", ""))
        container = database.get_container_client(os.getenv("COSMOS_JUDGE_TABLE", ""))
        query = "SELECT * FROM judges"
        parameters = []
        if name:
            query += " WHERE judges.name LIKE @judge_name"
            parameters.append({"name": "@judge_name", "value": f"%{name}%"})
        if email:
            if "WHERE" in query:
                query += " OR judges.email LIKE @judge_email"
            else:
                query += " WHERE judges.email LIKE @judge_email"
            parameters.append({"name": "@judge_email", "value": f"%{email}%"})
        judges = [item async for item in container.query_items(query=query, parameters=parameters)]
    response_body: SuccessMessage = SuccessMessage(
        title=f"{len(judges)} Judges Retrieved",
        message="Successfully retrieved judge data from the database.",
        content=judges,
    )
    return JSONResponse(status_code=status.HTTP_200_OK, content=jsonable_encoder(response_body))


@app.post("/create-judge", tags=["Judges"])
async def create_judge(judge: Judge) -> JSONResponse:
    """ """
    async with CosmosClient(COSMOS_ENDPOINT, DefaultAzureCredential()) as cosmos_client:
        try:
            database = cosmos_client.get_database_client(os.getenv("COSMOS_DB_NAME", ""))
            database.read()
        except exceptions.CosmosResourceNotFoundError:
            cosmos_client.create_database(os.getenv("COSMOS_DB_NAME", ""))
        container = database.get_container_client(os.getenv("COSMOS_JUDGE_TABLE", ""))
        await container.upsert_item(judge.model_dump())
    response_body: SuccessMessage = SuccessMessage(
        title=f"Judge {judge.name} Created",
        message="Judge created and ready for usage.",
        content=judge.model_dump(),
    )
    return JSONResponse(status_code=status.HTTP_200_OK, content=jsonable_encoder(response_body))


@app.put("/update-judge/{judge_id}", tags=["Judges"])
async def update_judge(judge_id: str, judge: Judge) -> JSONResponse:
    """ """
    async with CosmosClient(COSMOS_ENDPOINT, DefaultAzureCredential()) as cosmos_client:
        try:
            database = cosmos_client.get_database_client(os.getenv("COSMOS_DB_NAME", ""))
            database.read()
        except exceptions.CosmosResourceNotFoundError:
            raise HTTPException(status_code=404, detail="Database not found.")

        container = database.get_container_client(os.getenv("COSMOS_JUDGE_TABLE", ""))
        try:
            existing_client = await container.read_item(item=judge_id, partition_key=judge_id)
        except exceptions.CosmosResourceNotFoundError:
            raise HTTPException(status_code=404, detail="Judge not found.")

        updated_judge = {**existing_client, **judge.model_dump()}
        await container.replace_item(item=judge_id, body=updated_judge)

    response_body: SuccessMessage = SuccessMessage(
        title=f"Judge {judge.name} Updated",
        message="Judge data has been updated successfully.",
        content=updated_judge,
    )
    return JSONResponse(status_code=status.HTTP_200_OK, content=jsonable_encoder(response_body))


@app.delete("/delete-judge/{judge_id}", tags=["Judge"])
async def delete_judge(judge_id: str) -> JSONResponse:
    """ """
    async with CosmosClient(COSMOS_ENDPOINT, DefaultAzureCredential()) as cosmos_client:
        try:
            database = cosmos_client.get_database_client(os.getenv("COSMOS_DB_NAME", ""))
            database.read()
        except exceptions.CosmosResourceNotFoundError:
            raise HTTPException(status_code=404, detail="Database not found.")

        container = database.get_container_client(os.getenv("COSMOS_JUDGE_TABLE", ""))
        try:
            await container.delete_item(item=judge_id, partition_key=judge_id)
        except exceptions.CosmosResourceNotFoundError:
            raise HTTPException(status_code=404, detail="Judge not found.")

    response_body: SuccessMessage = SuccessMessage(
        title=f"Judge {judge_id} Deleted",
        message="Judge has been deleted successfully.",
        content={"judge_id": judge_id},
    )
    return JSONResponse(status_code=status.HTTP_200_OK, content=jsonable_encoder(response_body))


@app.get("/list-assemblies", tags=["Assembly"])
async def list_assemblies(role: Optional[str] = None) -> JSONResponse:
    """ """
    async with CosmosClient(COSMOS_ENDPOINT, DefaultAzureCredential()) as client:
        try:
            database = client.get_database_client(os.getenv("COSMOS_DB_NAME", ""))
            database.read()
        except exceptions.CosmosResourceNotFoundError:
            client.create_database(os.getenv("COSMOS_DB_NAME", ""))
        container = database.get_container_client(os.getenv("COSMOS_ASSEMBLY_TABLE", ""))
        query = "SELECT * FROM c"
        parameters = []
        if role:
            query += " WHERE c.roles LIKE @role"
            parameters.append({"name": "@role", "value": f"%{role}%"})
        assemblies = [
            item async for item in container.query_items(query=query, parameters=parameters)
        ]
    response_body: SuccessMessage = SuccessMessage(
        title=f"{len(assemblies)} Assemblies Retrieved",
        message="Successfully retrieved assemblies with proper filter.",
        content=assemblies,
    )
    return JSONResponse(status_code=status.HTTP_200_OK, content=jsonable_encoder(response_body))


@app.post("/create-assembly", tags=["Assembly"])
async def create_assembly(assembly: Assembly) -> JSONResponse:
    """ """
    async with CosmosClient(COSMOS_ENDPOINT, DefaultAzureCredential()) as cosmos_client:
        try:
            database = cosmos_client.get_database_client(os.getenv("COSMOS_DB_NAME", ""))
            database.read()
        except exceptions.CosmosResourceNotFoundError:
            cosmos_client.create_database(os.getenv("COSMOS_DB_NAME", ""))
        container = database.get_container_client(os.getenv("COSMOS_ASSEMBLY_TABLE", ""))
        await container.upsert_item(assembly.model_dump())
    response_body: SuccessMessage = SuccessMessage(
        title="Email Created",
        message="Email content has been created successfully.",
        content=assembly.model_dump(),
    )
    return JSONResponse(status_code=status.HTTP_200_OK, content=jsonable_encoder(response_body))


@app.put("/update-assembly/{assembly_id}", tags=["Assembly"])
async def update_assembly(assembly_id: str, assembly: Assembly) -> JSONResponse:
    """ """
    async with CosmosClient(COSMOS_ENDPOINT, DefaultAzureCredential()) as cosmos_client:
        try:
            database = cosmos_client.get_database_client(os.getenv("COSMOS_DB_NAME", ""))
            database.read()
        except exceptions.CosmosResourceNotFoundError:
            raise HTTPException(status_code=404, detail="Database not found.")

        container = database.get_container_client(os.getenv("COSMOS_ASSEMBLY_TABLE", ""))
        try:
            existing_assembly = await container.read_item(
                item=assembly_id, partition_key=assembly_id
            )
        except exceptions.CosmosResourceNotFoundError:
            raise HTTPException(status_code=404, detail="Assembly not found.")

        updated_assembly = {**existing_assembly, **assembly.model_dump()}
        await container.replace_item(item=assembly_id, body=updated_assembly)

    response_body: SuccessMessage = SuccessMessage(
        title=f"Assembly {assembly_id} Updated",
        message="Assembly content has been updated successfully.",
        content=updated_assembly,
    )
    return JSONResponse(status_code=status.HTTP_200_OK, content=jsonable_encoder(response_body))


@app.delete("/delete-assembly/{assembly_id}", tags=["Assembly"])
async def delete_email(assembly_id: str) -> JSONResponse:
    """ """
    async with CosmosClient(COSMOS_ENDPOINT, DefaultAzureCredential()) as cosmos_client:
        try:
            database = cosmos_client.get_database_client(os.getenv("COSMOS_DB_NAME", ""))
            database.read()
        except exceptions.CosmosResourceNotFoundError:
            raise HTTPException(status_code=404, detail="Database not found.")

        container = database.get_container_client(os.getenv("COSMOS_ASSEMBLY_TABLE", ""))
        try:
            await container.delete_item(item=assembly_id, partition_key=assembly_id)
        except exceptions.CosmosResourceNotFoundError:
            raise HTTPException(status_code=404, detail="Email not found.")

    response_body: SuccessMessage = SuccessMessage(
        title=f"Email {assembly_id} Deleted",
        message="Email content has been deleted successfully.",
        content={"email_id": assembly_id},
    )
    return JSONResponse(status_code=status.HTTP_200_OK, content=jsonable_encoder(response_body))


@app.post("/evaluate", tags=["Judges", "Assembly"])
async def evaluate_judgment(evaluation: JudgeEvaluation) -> JSONResponse:
    """
    Endpoint that evaluates a prompt using a Judge Assembly.

    Process:
      1. Retrieve the Assembly document (which contains judge configurations) from Cosmos DB.
      2. Convert the document to an Assembly Pydantic model.
      3. Use JudgeOrchestrator to:
           - Build a shared Kernel.
           - Create a SuperJudge and individual ConcreteJudge agents.
           - Register all sub-judges with the SuperJudge.
           - Run the evaluation (the SuperJudge invokes its plan to run all sub-judges).
      4. Return the final aggregated verdict as a JSON response.
    """
    # 1. Retrieve the assembly document
    assembly_doc = await fetch_assembly(evaluation.id)
    if not assembly_doc:
        raise HTTPException(status_code=404, detail=f"Assembly '{evaluation.id}' not found.")

    # 2. Convert to a Pydantic Assembly model
    assembly = Assembly(**assembly_doc)

    # 3. Run the evaluation using the orchestrator
    try:
        final_verdict = await JudgeOrchestrator.run_evaluation(assembly, evaluation.prompt)
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))

    # 4. Return the final verdict
    response_body = SuccessMessage(
        title="Evaluation Complete",
        message="Judging completed successfully.",
        content={"assembly_id": evaluation.id, "result": final_verdict},
    )
    return JSONResponse(status_code=status.HTTP_200_OK, content=jsonable_encoder(response_body))
