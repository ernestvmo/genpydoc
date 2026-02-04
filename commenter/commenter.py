import asyncio
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI as AsyncOpenAIClient
from timeit import default_timer as timer

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

    def __init_client(self):
        self._model = self.config.use_model
        if self.config.use_llm_provider == "openai":  # todo other api?
            if not OPENAI_API_KEY:
                raise EnvironmentError("No API key.")
            self._client_api = AsyncOpenAIClient(api_key=OPENAI_API_KEY)

    def build_prompt(self, node: CovNode) -> str:
        # TODO now we will always be checking covered node, consider future cover all uncovered?
        return (
            f"You are a senior python engineer. Analyze the following code block between <code.start> and <code.end>:\n\n<code.start>\n{node.code}\n<code.end>\n\n"
            f"This is the current docstring between <doc.start> and <doc.end>:\n\n<doc.start>\n{node.docstring}\n<doc.end>\n\n"
            f"I want you to analyze the purpose of the code segment, and write a new docstring for {node.name} (and only for {node.name}).\n"
            f"The docstring must be using {self.config.docstring_style} style. "
            "If the old docstring correctly reflects the purpose of the code segment, return -1, else return only the docstring."
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
    ):
        if self.config.use_llm_provider == "openai":
            await self.openai_process(prompt, node_name, responses)

    async def process_prompts(self, prompts: dict[str, str]) -> dict[str, str]:
        responses = {}
        start = timer()
        async with asyncio.TaskGroup() as tg:  # 27.41 seconds.
            for name, prompt in prompts.items():
                tg.create_task(self.process_prompt(prompt, name, responses))
        end = timer()
        print(f"Generated stories sequentially in {end - start:.2f} seconds.")
        return responses

    async def comment(self, nodes: list[CovNode]):
        prompts = {node.name: self.build_prompt(node=node) for node in nodes}
        comments = await self.process_prompts(prompts=prompts)
        return comments

    def document(self, nodes: dict[str, list[CovNode]]):
        documented = {}
        for k in nodes:
            docs = asyncio.run(self.comment(nodes[k]))
            documented[k] = docs
        return documented
