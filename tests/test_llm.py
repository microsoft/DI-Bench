from bigbuild.utils.llm.provider.azure import AzureOpenaiProvider
import pytest

@pytest.mark.skip(reason="local only")
def test_request():
    provider = AzureOpenaiProvider("gpt-4o-20240806")
    print(provider.generate_reply("hello world"))

if __name__ == "__main__":
    test_request()