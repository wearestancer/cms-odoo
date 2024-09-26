from glob import iglob
from pathlib import Path
from zipfile import ZipFile


def create_archive():
    """Create a zipfile ready to be used in odoo."""
    module_folder = "payment_stancer"
    with ZipFile(f"{module_folder}.zip", "w") as myzip:
        for filename in iglob(module_folder + "**/*", recursive=True):
            path = Path(filename).relative_to(module_folder)
            myzip.write(filename, path)

        myzip.write("./requirements.txt")
        myzip.write("README.md")


if __name__ == "__main__":
    create_archive()
