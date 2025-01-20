from .prompt import (
    CSHARP_ENV_PROMPT,
    JAVA_ENV_PROMPT,
    PYTHON_ENV_PROMPT,
    RUST_ENV_PROMPT,
    TS_ENV_PROMPT,
)


def make_prompt(language: str):
    language = language.lower()
    if language == "python":
        return PYTHON_ENV_PROMPT
    if language == "csharp":
        return CSHARP_ENV_PROMPT
    if language == "rust":
        return RUST_ENV_PROMPT
    if language == "typescript" or language == "javascript":
        return TS_ENV_PROMPT
    if language == "java":
        return JAVA_ENV_PROMPT
    raise Exception(f"Unknown language: {language}")
