import asyncio
import os
from pathlib import Path
from timeit import default_timer as timer
from dotenv import load_dotenv
from openai import AsyncOpenAI as AsyncOpenAIClient
from tqdm import tqdm
from genpydoc.commenter.transformer import Parser
from genpydoc.config.config import Config
from genpydoc.extractor.visit import CovNode

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


class Commenter:
    """Commenter is responsible for generating or updating docstrings for Python code using a configured large language model (LLM) backend. It builds prompts for classes and functions, queries the LLM, collects the responses, and applies the resulting documentation to source files via a Parser.

    Attributes:
        MODELS_MAPPING (dict): Mapping of provider keys to model identifiers.
        _model (str): Name of the selected model for the current run.
        _client_api (AsyncOpenAIClient): Client used to communicate with the OpenAI API.
        config (Config): Runtime configuration object with settings like provider, API key, and docstring style.
        parser (Parser): Parser instance used to process and attach generated docs to files.
    """

    MODELS_MAPPING: dict = {"openai": "gpt-5-nano"}
    _model: str = None
    _client_api: AsyncOpenAIClient

    def __init__(self, config: Config):
        self.config = config
        self.__init_client()
        self.parser = Parser(config=config)

    def __init_client(self) -> None:
        self._model = self.config.use_model
        if self.config.use_llm_provider == "openai":
            if not OPENAI_API_KEY:
                raise EnvironmentError("No API key.")
            self._client_api = AsyncOpenAIClient(api_key=OPENAI_API_KEY)

    def build_prompt(self, node: CovNode) -> str:
        if node.node_type == "ClassDef":
            return self.build_class_prompt(node)
        elif node.node_type in ["FunctionDef", "AsyncFunctionDef"]:
            return self.build_function_prompt(node)
        return ""

    def build_class_prompt(self, node: CovNode) -> str:
        return (
            f"You are a senior python engineer. Analyze the following class between <code.start> and <code.end>:\n\n<code.start>\n{node.code}\n<code.end>\n\n"
            + (
                f"This is the current docstring between <doc.start> and <doc.end>:\n\n<doc.start>\n{node.docstring}\n<doc.end>\n\n"
                if node.docstring
                else ""
            )
            + f"I want you to analyze the purpose of the class, and write a new docstring for {node.name} (and only for {node.name}).\nThe docstring must be using {self.config.docstring_style} style. Since this is a class, only write a description for the purpose of the class, and list the attributes. If the old docstring correctly reflects the purpose of the code segment, return -1, else return only the docstring."
        )

    def build_function_prompt(self, node: CovNode) -> str:
        return (
            f"You are a senior python engineer. Analyze the following code block between <code.start> and <code.end>:\n\n<code.start>\n{node.code}\n<code.end>\n\n"
            + (
                f"This is the current docstring between <doc.start> and <doc.end>:\n\n<doc.start>\n{node.docstring}\n<doc.end>\n\n"
                if node.docstring
                else ""
            )
            + f"I want you to analyze the purpose of the code segment, and write a new docstring for {node.name} (and only for {node.name}).\nThe docstring must be using {self.config.docstring_style} style. You must only write a description of the function, list the attributes with a basic description, explain any errors raised. Only explicitly show a return if the function returns something not None. If the old docstring correctly reflects the purpose of the code segment, return -1, else return only the docstring."
        )

    async def openai_process(
        self, prompt: str, node_name: str, responses: dict[str, str]
    ) -> None:
        response = await self._client_api.responses.create(
            model=self._model, input=prompt
        )
        responses[node_name] = response.output_text

    async def process_prompt(
        self, prompt: str, node_name: str, responses: dict[str, str]
    ) -> None:
        if self.config.use_llm_provider == "openai":
            await self.openai_process(prompt, node_name, responses)

    async def process_prompts(self, prompts: dict[str, str]) -> dict[str, str]:
        """Process a batch of prompts concurrently and collect their results.

        This coroutine schedules one task per prompt to be processed by
        `self.process_prompt`, all executed concurrently within the same event loop.
        Results are accumulated in a shared dictionary keyed by the prompt name, and
        a progress bar is shown while processing.

        Args:
            prompts (dict[str, str]):
                A mapping from a unique name to the prompt text that should be
                processed. Each entry yields a corresponding entry in the returned
                dictionary with the same name as key and the generated response as value.

        Returns:
            dict[str, str]:
                A dictionary mapping each prompt name to its generated response.

        Notes:
            - Exceptions raised by individual tasks are caught and reported via
              tqdm.write; processing continues for other prompts and the function
              completes once all tasks are done.
            - The function mutates a shared dictionary from multiple coroutines; if
              self.process_prompt does not coordinate writes safely, a race condition
              could occur. In CPython, dict writes are generally atomic due to the GIL
              in a single-threaded event loop.
        """
        responses = {}
        start = timer()
        tasks = [
            asyncio.create_task(self.process_prompt(prompt, name, responses))
            for name, prompt in prompts.items()
        ]
        with tqdm(
            total=len(tasks), desc="Commenting", unit="block", leave=True
        ) as pbar:
            for fut in asyncio.as_completed(tasks):
                try:
                    await fut
                except Exception as e:
                    tqdm.write(f"[error]: a task failed: {e!r}")
                finally:
                    pbar.update(1)
        end = timer()
        print(f"Generated comments concurrently in {end - start:.2f} seconds.")
        return responses

    async def comment(self, nodes: list[CovNode]) -> dict[str, str]:
        not_ignored = [
            n
            for n in nodes
            if n.node_type in ["ClassDef", "FunctionDef", "AsyncFunctionDef"]
        ]
        prompts = {
            node.name: self.build_prompt(node=node) for node in not_ignored
        }
        comments = await self.process_prompts(prompts=prompts)
        return comments

    def document(self, nodes: dict[str, list[CovNode]]) -> None:
        for file in nodes:
            print(f"Checking file: {file}.", end="\t")
            docs = asyncio.run(self.comment(nodes[file]))
            docs = {k: v for k, v in docs.items() if v != "-1"}
            self.parser.process(Path(file), docs)
