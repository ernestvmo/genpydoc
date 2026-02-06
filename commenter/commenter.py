import asyncio
import os
from pathlib import Path
from timeit import default_timer as timer

from dotenv import load_dotenv
from openai import AsyncOpenAI as AsyncOpenAIClient
from tqdm import tqdm

from commenter.transformer import Parser
from config.config import Config
from extractor.visit import CovNode

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


class Commenter:
    MODELS_MAPPING: dict = {
        "openai": "gpt-5-nano",
    }

    _model: str = None
    _client_api: AsyncOpenAIClient

    def __init__(self, config: Config):
        self.config = config
        self.__init_client()
        self.parser = Parser(config=config)

    def __init_client(self):
        self._model = self.config.use_model
        if self.config.use_llm_provider == "openai":  # todo other api?
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
            + f"I want you to analyze the purpose of the class, and write a new docstring for {node.name} (and only for {node.name}).\n"
            f"The docstring must be using {self.config.docstring_style} style. Since this is a class, only write a description for the purpose of the class, and list the attributes. "
            "If the old docstring correctly reflects the purpose of the code segment, return -1, else return only the docstring."
        )

    def build_function_prompt(self, node: CovNode) -> str:
        return (
            f"You are a senior python engineer. Analyze the following code block between <code.start> and <code.end>:\n\n<code.start>\n{node.code}\n<code.end>\n\n"
            + (
                f"This is the current docstring between <doc.start> and <doc.end>:\n\n<doc.start>\n{node.docstring}\n<doc.end>\n\n"
                if node.docstring
                else ""
            )
            + f"I want you to analyze the purpose of the code segment, and write a new docstring for {node.name} (and only for {node.name}).\n"
            f"The docstring must be using {self.config.docstring_style} style. You must only write a description of the function, "
            f"list the attributes with a basic description, explain any errors raised. Only explicitly show a return if the function returns something not None. "
            "If the old docstring correctly reflects the purpose of the code segment, return -1, else return only the docstring."
        )

    async def openai_process(self, prompt: str, node_name: str, responses: dict[str, str]) -> None:
        response = await self._client_api.responses.create(model=self._model, input=prompt)
        responses[node_name] = response.output_text

    async def process_prompt(self, prompt: str, node_name: str, responses: dict[str, str]):
        if self.config.use_llm_provider == "openai":
            await self.openai_process(prompt, node_name, responses)

    async def process_prompts(self, prompts: dict[str, str]) -> dict[str, str]:
        responses = {}
        start = timer()

        tasks = [asyncio.create_task(self.process_prompt(prompt, name, responses)) for name, prompt in prompts.items()]

        with tqdm(total=len(tasks), desc="Commenting", unit="block", leave=True) as pbar:
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

    async def comment(self, nodes: list[CovNode]):
        not_ignored = [n for n in nodes if n.node_type in ["ClassDef", "FunctionDef", "AsyncFunctionDef"]]
        prompts = {node.name: self.build_prompt(node=node) for node in not_ignored}
        comments = await self.process_prompts(prompts=prompts)
        return comments

    def document(self, nodes: dict[str, list[CovNode]]) -> None:
        for k in nodes:
            print(f"Checking file: {k}.", end="\t")
            docs = asyncio.run(self.comment(nodes[k]))
            self.parser.process(Path(k), docs)
