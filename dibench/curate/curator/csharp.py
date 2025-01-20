import glob
import os
from pathlib import Path

from lxml import etree

from .base import Curator


class CsharpCurator(Curator):
    def set_build_files(self) -> None:
        csproj_files = glob.glob(
            os.path.join(self.root, "**", "*.csproj"), recursive=True
        )
        build_files = []

        for csproj_file in csproj_files:
            self.logger.info(f">>> Set Build Files >>> Checking {csproj_file}")
            tree = etree.parse(csproj_file)
            root = tree.getroot()

            nsmap = root.nsmap
            default_ns = nsmap.get(None)

            ns = {"ns": default_ns} if default_ns else {}
            item_group_xpath = ".//ns:ItemGroup" if default_ns else ".//ItemGroup"
            project_ref_xpath = (
                "ns:ProjectReference" if default_ns else "ProjectReference"
            )
            package_ref_xpath = (
                "ns:PackageReference" if default_ns else "PackageReference"
            )

            for item_group in root.findall(item_group_xpath, namespaces=ns):
                project_refs = item_group.findall(project_ref_xpath, namespaces=ns)
                package_refs = item_group.findall(package_ref_xpath, namespaces=ns)

                if project_refs or package_refs:
                    self.logger.info(">>> Found build file")
                    build_files.append(os.path.relpath(csproj_file, self.root))
                    break

        self.logger.info(f"Found {len(build_files)} build files:\n{build_files}")

        self.instance.build_files = build_files

    def mask(self) -> None:
        for build_file in self.build_files:
            self.logger.info(f">>> Masking {build_file}")
            file = Path(self.root) / build_file
            with open(file, "r", newline="") as f:
                lines = f.readlines()
            tree = etree.parse(file)
            root = tree.getroot()

            nsmap = root.nsmap
            default_ns = nsmap.get(
                None
            )  # None key corresponds to the default namespace

            ns = {"ns": default_ns} if default_ns else {}

            item_group_xpath = ".//ns:ItemGroup" if default_ns else ".//ItemGroup"
            project_ref_xpath = (
                "ns:ProjectReference" if default_ns else "ProjectReference"
            )
            package_ref_xpath = (
                "ns:PackageReference" if default_ns else "PackageReference"
            )

            item_groups = root.findall(item_group_xpath, namespaces=ns)

            item_groups_to_remove = []

            for item_group in item_groups:
                has_project_ref = (
                    item_group.find(project_ref_xpath, namespaces=ns) is not None
                )
                has_package_ref = (
                    item_group.find(package_ref_xpath, namespaces=ns) is not None
                )
                if has_project_ref or has_package_ref:
                    item_groups_to_remove.append(item_group)

            elems = item_groups_to_remove

            self.logger.info(f"Found {len(elems)} elements to mask")

            def find_line_numbers(element):
                start_line = element.sourceline
                _start_line = start_line
                # remove empty line before the element
                if lines[start_line - 2].strip() == "":
                    _start_line = start_line - 1
                elem_string = etree.tostring(element).decode("utf-8").strip()
                elem_lines = elem_string.splitlines()
                end_line = start_line + len(elem_lines) - 1
                return list(range(_start_line, end_line + 1))

            linenos = []
            for elem in elems:
                linenos.extend(find_line_numbers(elem))

            self.logger.info(f"Found {len(linenos)} lines to mask: {linenos}")

            linenos.sort(reverse=True)

            for lineno in linenos:
                del lines[lineno - 1]

            with open(file, "w", newline="") as f:
                f.writelines(lines)

        self.commit("MASK")

    def sanitize(self) -> None:
        lock_files = list(self.root.rglob("packages.lock.json"))
        for lock_file in lock_files:
            self.logger.info(f"Deleting {lock_file}")
            lock_file.unlink()
        if lock_files == []:
            self.logger.info("GOOD: No lock files found")
            return
        self.commit
