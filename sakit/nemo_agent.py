import asyncio
import logging
import os
import shutil
import zipfile
import uuid  # For unique S3 object keys if not specified
from typing import Dict, Any, List, Optional

from solana_agent import AutoTool, ToolRegistry

try:
    from nemo_agent import NemoAgent  # User's current import

    NEMO_AGENT_AVAILABLE = True
except ImportError:
    NEMO_AGENT_AVAILABLE = False
    NemoAgent = None  # type: ignore
    logging.error(
        "NemoAgentPlugin: Failed to import NemoAgent from 'nemo_agent'. "
        "Ensure the NemoAgent library/module is correctly installed or accessible. "
        "The NemoAgentTool plugin will not function."
    )

# --- Boto3 Import (Optional for S3 upload) ---
try:
    import boto3  # type: ignore
    from botocore.exceptions import (
        NoCredentialsError,
        PartialCredentialsError,
        ClientError,
    )  # type: ignore

    BOTO3_AVAILABLE = True
except ImportError:
    boto3 = None  # type: ignore
    NoCredentialsError = None  # type: ignore
    PartialCredentialsError = None  # type: ignore
    ClientError = None  # type: ignore
    BOTO3_AVAILABLE = False
    # Warning will be logged if S3 upload is attempted without boto3

# --- Setup Logger ---
logger = logging.getLogger(__name__)


class NemoAgentTool(AutoTool):
    """
    A tool for developing Python projects using NemoAgent,
    with optional S3 upload for the zipped project.
    """

    def __init__(self, registry: Optional[ToolRegistry] = None):
        super().__init__(
            name="nemo_agent",  # Changed tool name
            description=(
                "Creates, implements, and tests Python projects using NemoAgent. "
                "Handles dependencies (uv) and testing (pytest). "
                "Can optionally upload the zipped project to S3."
            ),
            registry=registry,
        )

        # NemoAgent execution config
        self._nemo_provider: str = "openai"  # Default provider
        self._nemo_model: str = "gpt-4.1"  # Default model, will be overridden by config
        self._nemo_api_key: Optional[str] = None

        # S3 related attributes
        self._s3_endpoint_url: Optional[str] = None
        self._s3_access_key_id: Optional[str] = None
        self._s3_secret_access_key: Optional[str] = None
        self._s3_bucket_name: Optional[str] = None
        self._s3_region_name: Optional[str] = None
        self._s3_public_url_base: Optional[str] = None
        self._s3_object_key_prefix: str = "nemo_projects/"  # Default prefix

        logger.debug("NemoAgentTool initialized.")

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "Detailed description of the programming task or project for NemoAgent.",
                },
                "run_tests": {
                    "type": "boolean",
                    "description": "Whether NemoAgent should run tests. Defaults to True.",
                    "default": True,
                },
            },
            "required": ["task", "run_tests"],
            "additionalProperties": False,
        }

    def configure(self, config: Dict[str, Any]) -> None:
        super().configure(config)

        # Configuration for NemoAgent execution and S3 from tool-specific config
        if (
            "tools" in config
            and isinstance(config["tools"], dict)
            and "nemo_agent" in config["tools"]
            and isinstance(config["tools"]["nemo_agent"], dict)
        ):
            tool_config = config["tools"]["nemo_agent"]

            # NemoAgent provider and model config
            self._nemo_provider = tool_config.get("provider", "openai").lower()
            self._nemo_api_key = tool_config.get("api_key")
            if self._nemo_provider == "openai":
                openai_config = tool_config.get("openai", {})
                self._nemo_model = openai_config.get(
                    "model", "gpt-4.1"
                )  # Default OpenAI model
            elif self._nemo_provider == "gemini":
                gemini_config = tool_config.get("gemini", {})
                self._nemo_model = gemini_config.get(
                    "model", "gemini-2.5-pro-preview-05-06"
                )  # Default Gemini model
            else:
                logger.warning(
                    f"NemoAgentTool: Unknown provider '{self._nemo_provider}'. Defaulting to OpenAI and its default model."
                )
                self._nemo_provider = "openai"
                self._nemo_model = "gpt-4.1"
            logger.info(
                f"NemoAgentTool: Configured to use NemoAgent with provider '{self._nemo_provider}' and model '{self._nemo_model}'."
            )

            # S3 Configuration
            self._s3_endpoint_url = tool_config.get("s3_endpoint_url")
            self._s3_access_key_id = tool_config.get("s3_access_key_id")
            self._s3_secret_access_key = tool_config.get("s3_secret_access_key")
            self._s3_bucket_name = tool_config.get("s3_bucket_name")
            self._s3_region_name = tool_config.get("s3_region_name")
            self._s3_public_url_base = tool_config.get("s3_public_url_base")
            self._s3_object_key_prefix = tool_config.get(
                "s3_object_key_prefix", "nemo_projects/"
            )
            if not self._s3_object_key_prefix.endswith("/"):
                self._s3_object_key_prefix += "/"

            if all(
                [
                    self._s3_endpoint_url,
                    self._s3_access_key_id,
                    self._s3_secret_access_key,
                    self._s3_bucket_name,
                ]
            ):
                logger.info(
                    f"NemoAgentTool: S3 upload configured and enabled. Endpoint: {self._s3_endpoint_url}, Bucket: {self._s3_bucket_name}"
                )
            else:
                logger.warning(
                    "NemoAgentTool: S3 upload enabled but S3 configuration is incomplete. Upload will likely fail."
                )

        logger.info("NemoAgentTool configured.")

    def _is_s3_fully_configured(self) -> bool:
        return bool(
            BOTO3_AVAILABLE
            and self._s3_endpoint_url
            and self._s3_access_key_id
            and self._s3_secret_access_key
            and self._s3_bucket_name
        )

    def _upload_zip_to_s3(self, zip_file_path: str, object_key: str) -> Optional[str]:
        if not self._is_s3_fully_configured():
            logger.error(
                "S3 upload attempted but S3 is not fully configured or boto3 is unavailable."
            )
            return None
        if not boto3:
            logger.error("Boto3 library not available for S3 upload.")
            return None
        try:
            s3_client = boto3.client(
                "s3",
                aws_access_key_id=self._s3_access_key_id,
                aws_secret_access_key=self._s3_secret_access_key,
                endpoint_url=self._s3_endpoint_url,
                region_name=self._s3_region_name,
            )
            with open(zip_file_path, "rb") as f:
                s3_client.upload_fileobj(
                    f,
                    self._s3_bucket_name,
                    object_key,
                    ExtraArgs={"ContentType": "application/zip", "ACL": "public-read"},
                )
            logger.info(
                f"Successfully uploaded ZIP to S3: s3://{self._s3_bucket_name}/{object_key}"
            )

            if self._s3_public_url_base:
                base = (
                    self._s3_public_url_base
                    if self._s3_public_url_base.endswith("/")
                    else self._s3_public_url_base + "/"
                )
                public_url = base + object_key
            else:
                endpoint_base = self._s3_endpoint_url.replace("https://", "")
                public_url = (
                    f"https://{self._s3_bucket_name}.{endpoint_base}/{object_key}"
                )
            logger.info(f"Public S3 URL for ZIP: {public_url}")
            return public_url
        except (NoCredentialsError, PartialCredentialsError):  # type: ignore
            logger.error("S3 credentials not found or incomplete for ZIP upload.")
        except ClientError as e:  # type: ignore
            logger.error(f"S3 ClientError during ZIP upload: {e}")
        except Exception as e:
            logger.exception(f"Unexpected error during S3 ZIP upload: {e}")
        return None

    async def execute(self, **kwargs) -> Dict[str, Any]:
        if not NEMO_AGENT_AVAILABLE or NemoAgent is None:
            return {
                "status": "error",
                "message": "NemoAgent module is not available. NemoAgentTool cannot execute.",
            }

        task = kwargs.get("task")
        if not task:
            return {"status": "error", "message": "Missing required parameter: task."}

        run_tests_flag = kwargs.get("run_tests", True)
        output_zip_name_arg = kwargs.get("output_zip_name")
        s3_object_name_arg = kwargs.get("s3_object_name")

        original_cwd = os.getcwd()
        project_dir_path = None
        local_zip_path = None
        s3_zip_url = None
        final_message = ""

        try:
            logger.info(
                f"NemoAgentTool: Initializing NemoAgent for task: '{task[:50]}...' "
                f"with provider '{self._nemo_provider}' and model '{self._nemo_model}'."
            )
            # NemoAgent constructor takes model and provider
            nemo_agent_instance = NemoAgent(
                task=task,
                model=self._nemo_model,
                provider=self._nemo_provider,
                tests=run_tests_flag,
                api_key=self._nemo_api_key,
            )

            logger.info("NemoAgentTool: Starting NemoAgent.run_task()...")
            await asyncio.to_thread(nemo_agent_instance.run_task)
            logger.info("NemoAgentTool: NemoAgent.run_task() completed.")

            project_dir_path = nemo_agent_instance.pwd
            final_message = (
                f"NemoAgent task completed. Project generated at: {project_dir_path}"
            )

            zip_basename = (
                output_zip_name_arg
                or f"{os.path.basename(project_dir_path or 'project')}_{uuid.uuid4().hex[:8]}.zip"
            )
            if not zip_basename.endswith(".zip"):
                zip_basename += ".zip"

            local_zip_path = os.path.join(original_cwd, zip_basename)

            logger.info(
                f"NemoAgentTool: Zipping project directory {project_dir_path} to {local_zip_path}"
            )
            with zipfile.ZipFile(local_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(project_dir_path):
                    for file_item in files:
                        file_path_to_zip = os.path.join(root, file_item)
                        arcname = os.path.relpath(file_path_to_zip, project_dir_path)
                        zipf.write(file_path_to_zip, arcname)
            logger.info(
                f"NemoAgentTool: Project successfully zipped locally to {local_zip_path}"
            )
            final_message += f". Zipped locally to {local_zip_path}."

            if self._is_s3_fully_configured():
                s3_key = s3_object_name_arg or (
                    self._s3_object_key_prefix + zip_basename
                )
                logger.info(
                    f"NemoAgentTool: Attempting S3 upload of {local_zip_path} to s3://{self._s3_bucket_name}/{s3_key}"
                )
                s3_zip_url = await asyncio.to_thread(
                    self._upload_zip_to_s3, local_zip_path, s3_key
                )
                if s3_zip_url:
                    final_message += f". Successfully uploaded to S3: {s3_zip_url}."
                    try:
                        os.remove(local_zip_path)
                        logger.info(
                            f"NemoAgentTool: Removed local zip file {local_zip_path} after S3 upload."
                        )
                        local_zip_path = None
                    except OSError as e_remove:
                        logger.error(
                            f"NemoAgentTool: Failed to remove local zip {local_zip_path} after S3 upload: {e_remove}"
                        )
                else:
                    final_message += ". S3 upload failed. Local zip file retained."
            else:
                logger.info(
                    "NemoAgentTool: S3 upload skipped (not configured, disabled, or boto3 missing)."
                )

            logger.info(
                f"NemoAgentTool: Deleting original project directory {project_dir_path}"
            )
            shutil.rmtree(project_dir_path)
            logger.info(
                f"NemoAgentTool: Original project directory {project_dir_path} deleted."
            )
            project_dir_path = None

            return_payload = {
                "status": "success",
                "message": final_message,
                "nemo_tokens_used": sum(nemo_agent_instance.token_counts.values())
                if hasattr(nemo_agent_instance, "token_counts")
                else "N/A",
            }
            if s3_zip_url:
                return_payload["result"] = f"The project ZIP S3 URL is {s3_zip_url}"
                return_payload["s3_zip_url"] = s3_zip_url
            if local_zip_path:
                return_payload["local_zip_path"] = local_zip_path
                if not s3_zip_url:  # If S3 upload failed or was skipped, make local path the primary result
                    return_payload["result"] = (
                        f"The project local ZIP path is {local_zip_path}"
                    )

            return return_payload

        except Exception as e:
            logger.exception(
                f"NemoAgentTool: Error during NemoAgent execution or zipping: {e}"
            )
            if local_zip_path and os.path.exists(local_zip_path) and not s3_zip_url:
                try:
                    os.remove(local_zip_path)
                except OSError:
                    pass
            if project_dir_path and os.path.exists(project_dir_path):
                try:
                    shutil.rmtree(project_dir_path)
                except OSError:
                    pass
            return {
                "status": "error",
                "message": f"NemoAgent execution/zipping failed: {str(e)}",
            }


class NemoAgentPlugin:  # Renamed plugin class
    """Plugin for providing code development tools via NemoAgent."""

    def __init__(self):
        self.name = "nemo_agent"  # Changed plugin name to match tool
        self.config = None
        self.tool_registry = None
        self._tool: Optional[NemoAgentTool] = None
        logger.info(f"Created NemoAgentPlugin object with name: {self.name}")

    @property
    def description(self):
        return "Plugin providing Python project development via NemoAgent, with optional S3 upload."

    def initialize(self, tool_registry: ToolRegistry) -> None:
        if not NEMO_AGENT_AVAILABLE:
            logger.error(
                "NemoAgentPlugin: Cannot initialize because NemoAgent module is not available."
            )
            return

        self.tool_registry = tool_registry
        logger.info(f"Initializing {self.name} plugin.")
        self._tool = NemoAgentTool(registry=tool_registry)  # Use NemoAgentTool

        registered_tool = tool_registry.get_tool(self._tool.name)
        if registered_tool:
            logger.info(
                f"{self.name} tool ('{self._tool.name}') registration verification: Success"
            )
        else:
            logger.error(
                f"{self.name} tool ('{self._tool.name}') registration verification: Failed"
            )

    def configure(self, config: Dict[str, Any]) -> None:
        if not NEMO_AGENT_AVAILABLE:
            logger.error(
                "NemoAgentPlugin: Cannot configure because NemoAgent module is not available."
            )
            return

        self.config = config
        logger.info(f"Configuring {self.name} plugin.")
        if self._tool:
            self._tool.configure(self.config)
            logger.info(f"{self.name} tool configured.")
        else:
            logger.warning(
                f"Warning: {self.name} tool instance not found during configuration."
            )

    def get_tools(self) -> List[AutoTool]:
        if not NEMO_AGENT_AVAILABLE:
            return []
        return [self._tool] if self._tool else []


def get_plugin():
    """Return plugin instance for registration."""
    if not NEMO_AGENT_AVAILABLE:
        logger.error(
            "NemoAgentPlugin: Not creating plugin instance as NemoAgent module is unavailable."
        )

        class DummyPlugin:
            name = "nemo_agent (disabled: NemoAgent module missing)"
            description = "NemoAgent module or its dependencies missing."

            def initialize(self, *args, **kwargs):
                pass

            def configure(self, *args, **kwargs):
                pass

            def get_tools(self):
                return []

        return DummyPlugin()
    return NemoAgentPlugin()
