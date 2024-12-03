from dataclasses import dataclass

import requests
from lxml import etree

from .base import BuildSystem


@dataclass
class CSharpDependency:
    name: str
    version: str
    external: bool


class CSharpBuildSystem(BuildSystem):
    @classmethod
    def is_fake_lib(cls, dependency: CSharpDependency) -> bool:
        assert dependency.external, "Only external dependencies can be fake"
        url = f"https://api.nuget.org/v3-flatcontainer/{dependency.name}/index.json"
        response = requests.get(url)
        return response.status_code != 200

    def parse_dependencies(self) -> dict[str, list[CSharpDependency]]:
        # parse xml, get PackageReference and ProjectReference in csproj
        dependencies = {}
        for build_file in self.build_files:
            packages = []
            build_file = self.root / build_file
            tree = etree.parse(build_file)
            root = tree.getroot()
            nsmap = root.nsmap
            default_ns = nsmap.get(
                None
            )  # None key corresponds to the default namespace
            ns = {"ns": default_ns} if default_ns else {}
            # find all PackageReference and ProjectReference
            item_group_xpath = ".//ns:ItemGroup" if default_ns else ".//ItemGroup"
            package_ref_xpath = (
                "ns:PackageReference" if default_ns else "PackageReference"
            )
            project_ref_xpath = (
                "ns:ProjectReference" if default_ns else "ProjectReference"
            )
            item_groups = root.findall(item_group_xpath, namespaces=ns)
            for item_group in item_groups:
                package_refs = item_group.findall(package_ref_xpath, namespaces=ns)
                for package_ref in package_refs:
                    name = package_ref.attrib["Include"]
                    version = package_ref.attrib.get("Version", "")
                    packages.append(CSharpDependency(name, version, external=True))
                project_refs = item_group.findall(project_ref_xpath, namespaces=ns)
                for project_ref in project_refs:
                    name = project_ref.attrib["Include"]
                    packages.append(CSharpDependency(name, "", external=False))
            dependencies[str(build_file.relative_to(self.root))] = packages
        return dependencies

    def dumps_dependencies(
        self, dependencies: dict[str, list[CSharpDependency]]
    ) -> dict[str, str]:
        raise NotImplementedError

    @property
    def language(self) -> str:
        return "xml"

    @property
    def example(self) -> str:
        return """\
file src/src.csproj
```xml
<?xml version="1.0" encoding="utf-8"?>
<Project Sdk="Microsoft.NET.Sdk">
    <PropertyGroup>
        <OutputType>Exe</OutputType>
        <TargetFramework>netcoreapp2.1</TargetFramework>
    </PropertyGroup>
</Project>

<ItemGroup>
    <PackageReference Include="Newtonsoft.Json" Version="12.0.3" />
    <PackageReference Include="Microsoft.Extensions.Logging" Version="2.2.0" />
    <PackageReference Include="Microsoft.Extensions.Logging" Version="2.2.0" />
</ItemGroup>

<ItemGroup>
    <ProjectReference Include="lib/lib.csproj" />
</ItemGroup>
```"""
