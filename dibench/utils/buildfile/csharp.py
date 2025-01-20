import os
from dataclasses import dataclass
from pathlib import Path

import requests
from lxml import etree

from .base import BuildFile


@dataclass
class CSharpDependency:
    name: str
    version: str
    external: bool

    def __hash__(self):
        return hash((self.name, self.version, self.external))


class CSharpBuildFile(BuildFile):
    @classmethod
    def is_fake_lib(cls, dependency: CSharpDependency, **kwargs) -> bool:
        """
        Check if a dependency is a fake dependency.

        The dependency must be an external one, i.e. not a project reference.
        The check is done by requesting the package's metadata from the NuGet API.
        If the package is not found, the status code is not 200, and the method returns True.
        Otherwise, the package is not fake, and the method returns False.
        """
        if dependency.external:
            url = f"https://api.nuget.org/v3-flatcontainer/{dependency.name}/index.json"
            response = requests.get(url)
            return response.status_code != 200
        root: Path = kwargs.get("project_root", None)
        if root is None:
            raise ValueError("For CSharp, project root is required")
        file: str = kwargs.get("build_file", None)
        if file is None:
            raise ValueError("For CSharp, build file is required")
        build_file = root / file
        assert (
            build_file.exists() and build_file.is_file()
        ), f"Build file {build_file} does not exist"
        depended_file = dependency.name
        # if is a windows path
        if "\\" in depended_file:
            depended_file = depended_file.replace("\\", "/")
        depended_file = os.path.join(str(build_file.parent), depended_file)
        return not os.path.exists(depended_file)

    def parse_dependencies(self) -> dict[str, list[CSharpDependency]]:
        # parse xml, get PackageReference and ProjectReference in csproj
        """
        Parse the csproj file to get PackageReference and ProjectReference.

        Iterate all build files, parse the xml, get all PackageReference and ProjectReference.
        For each PackageReference, create a CSharpDependency with the name and version, and external=True.
        For each ProjectReference, create a CSharpDependency with the name and empty version, and external=False.
        Return a dictionary of build file path to a list of dependencies.
        """

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
                    name = package_ref.attrib.get("Include")
                    if name is None:
                        name = package_ref.attrib.get("Update", None)
                    if name is None:
                        continue
                    version = package_ref.attrib.get("Version", "")
                    packages.append(CSharpDependency(name, version, external=True))
                project_refs = item_group.findall(project_ref_xpath, namespaces=ns)
                for project_ref in project_refs:
                    name = project_ref.attrib.get("Include", None)
                    if name is None:
                        name = project_ref.attrib.get("Update", None)
                    if name is None:
                        continue
                    packages.append(CSharpDependency(name, "", external=False))
            dependencies[str(build_file.relative_to(self.root))] = packages
        return dependencies

    def dumps_dependencies(
        self, dependencies: dict[str, list[CSharpDependency]]
    ) -> dict[str, str]:
        """
        Dump the dependencies to a string for each build file.

        Return a dictionary of build file path to the content of the updated build file.
        The content is a xml string, with the dependencies added as PackageReference or ProjectReference.
        """
        result = {}
        for build_file, packages in dependencies.items():
            build_file_path = self.root / build_file
            tree = etree.parse(build_file_path)
            root = tree.getroot()

            nsmap = root.nsmap
            default_ns = nsmap.get(None)
            ns = {"ns": default_ns} if default_ns else {}

            # remove to avoid duplicate, which is not allowed in csproj
            item_group_xpath = ".//ns:ItemGroup" if default_ns else ".//ItemGroup"
            for item_group in root.findall(item_group_xpath, namespaces=ns):
                if (
                    item_group.find(
                        "ns:PackageReference" if default_ns else "PackageReference",
                        namespaces=ns,
                    )
                    is not None
                    or item_group.find(
                        "ns:ProjectReference" if default_ns else "ProjectReference",
                        namespaces=ns,
                    )
                    is not None
                ):
                    root.remove(item_group)

            if any(p.external for p in packages):
                external_group = etree.Element("ItemGroup")
                for pkg in sorted(packages, key=lambda x: x.name):
                    if pkg.external:
                        ref = etree.Element("PackageReference")
                        ref.set("Include", pkg.name)
                        if pkg.version:
                            ref.set("Version", pkg.version)
                        external_group.append(ref)
                if len(external_group):
                    root.append(external_group)

            if any(not p.external for p in packages):
                internal_group = etree.Element("ItemGroup")
                for pkg in sorted(packages, key=lambda x: x.name):
                    if not pkg.external:
                        ref = etree.Element("ProjectReference")
                        ref.set("Include", pkg.name)
                        internal_group.append(ref)
                if len(internal_group):
                    root.append(internal_group)

            result[
                build_file
            ] = '<?xml version="1.0" encoding="utf-8"?>\n' + etree.tostring(
                root, encoding="unicode", pretty_print=True
            )

        return result

    @property
    def language(self) -> str:
        return "xml"

    @property
    def example(self) -> dict:
        return dict(
            file="src/src.csproj",
            content="""\
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
""",
        )
