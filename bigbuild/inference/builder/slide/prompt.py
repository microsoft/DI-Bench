"""make prompt """
system_prompt_template = """\
You are an expert in {language}.\
Your task is to complete the build files for the following {language} project.\
The project includes source and build files, but the build files are missing dependency-related configurations.\
Edit the build files to add the necessary dependency configurations to ensure successful building and running of the project.\
"""

file_content_template = """
file: {path}
```{language}
{content}
```
"""

instruction_template = """
Generate a list of updated build files to include the necessary dependency-related configurations \
so that the project can run and build successfully.

Every build file should follow the following format:

1. the file path, prefix with `file:`
2. the content of the file, wrapped in a code block ```{language}...```

Here is an example:
{example}
"""

prompt_template = """
### Instruction
{instruction}

#### Project Structure
{project_structure}

#### Environment Specifications
{env_specs}

#### Project Source Code
{code_section}

#### Incomplete Build Files
{build_files}

#### Steps to Think
1. Read the source code to identify dependencies.
2. Analyze dependencies and project structure to distinguish between internal and external dependencies.
3. Map relationships between the source code and build files to determine where dependency configurations should be added.
4. Edit the build files to include the necessary dependency configurations.

!> **Note:** The project may have multiple build files. Ensure that you update all build files with the necessary dependency configurations.
!> **Note:** You should only edit the files in the `Incomplete Build File` section.
!> **Note:** You should only edit the dependency configurations in the build files.


### Response
"""
