class ParamDocString:
    var: str
    type: str | None
    doc: str


class DocString:
    content: str
    params: list[ParamDocString]
    type: str | None
