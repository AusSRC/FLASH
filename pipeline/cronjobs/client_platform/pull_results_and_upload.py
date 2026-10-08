"""
Prepare Detection for Oracle & Prepare Spectral for Oracle move all
relevant files for a run into a folder, make a metadata.txt containing the
run info such as sbid, quality_flag, run type etc., zip it into a single zip
for transfer, move it into the transfer folder and mark it as complete. This
script just checks that folder for complete zips and archives them once it's
uploaded them to the database.
"""

from pathlib import Path
from typing import List, Tuple
import shutil
import subprocess
import paramiko
import os
import hashlib
import tarfile
import json
from enum import Enum, auto


HOST = str(os.environ['HPC_PLATFORM'])
USERNAME = str(os.environ['HPC_USER'])
REMOTE_DIR = Path(os.environ['HPC_SCRATCH']) / "outputs_to_transfer"
REMOTE_ARCHIVE_DIR = Path(os.environ['HPC_SCRATCH']) / "uploaded_outputs"
TMPDIR = Path(os.environ['TMPDIR'])
DATADIR = Path(os.environ['DATA'])
CONFIGPATH = "config"
FLASHPASS = str(os.environ['FLASHPASS'])


class RunType(Enum):
    """Controls the run types allowed, should probably be used everywhere but
    its needed here and much of the codebase is Bash"""
    SPECTRAL = auto()
    DETECTION = auto()
    MASKED = auto()
    INVERTED = auto()
    INVMASKED = auto()


def sha256_file(path: Path) -> str:
    """Creates the sha256 hash of a file"""
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def fetch_completed_outputs(
    sftp: paramiko.SFTPClient,
    local_dir: Path,
    remote_dir: Path,
) -> List[Tuple[Path, Path]]:
    """ Copies all outputs from linefinder runs to local VM"""

    zips = []

    entries = sftp.listdir_attr(str(remote_dir))

    completed_outputs = sorted(
        remote_dir / (entry.filename.removesuffix(".complete") + ".tar.gz")
        for entry in entries
        if entry.filename.endswith(".complete")
    )

    # Foreach completed run outputs tar
    print(f"Found {len(completed_outputs)} outputs to transfer:")
    for remote_path in completed_outputs:

        # Check Remote Hash
        checksum_file = remote_path.with_suffix("").with_suffix(".sha256")
        with sftp.open(str(checksum_file)) as f:
            remote_hash = f.read().decode().split()[0]

        # Set the local path to copy too & make it if its missing
        local_path = Path(local_dir) / remote_path.name
        local_path.parent.mkdir(parents=True, exist_ok=True)

        # Download from remote to local
        sftp.get(str(remote_path), str(local_path))

        # Make Local Hash
        local_hash = sha256_file(local_path)

        # Compare Hashes
        if remote_hash != local_hash:
            raise RuntimeError(f"Hash mismatch for {remote_path.name}")

        zips.append((local_path, remote_path))

    return zips


def unpack_outputs(file_path: Path, local_dir: Path) -> Path:
    """Unpacks output files from local dir/run_name.tar.gz to
    local dir/run_name, as all run_name.tar.gz are made so that they extract to
    a folder of their own name."""
    with tarfile.open(file_path, "r:gz") as tar:
        tar.extractall(path=local_dir)

    # Strip '.tar.gz' from the file name
    base_name = os.path.basename(file_path)
    folder_name = base_name.replace(".tar.gz", "")

    return Path(local_dir) / folder_name


def extract_meta_data(path_to_unpacked: Path) -> (
        Tuple[str, str, str, str]):
    """The DB upload script needs to know the runtype and quality flag of the
    outputs it is uploading. This function extracts them from the runs bundled
    metadata file.
     """

    with open(f"{path_to_unpacked}/metadata.json") as f:
        metadata = json.load(f)

    run_type = str(metadata['RUN_TYPE'])
    sbid = str(metadata["SBID"])
    quality = str(metadata["QUALITY"])
    comment = str(metadata["COMMENT"])

    return run_type, sbid, quality, comment


def move_outputs_to_upload_paths(
    path_to_unpacked: Path,
    run_type: str
):
    if run_type == "SPECTRAL":
        move_spectral_outputs(path_to_unpacked)

    elif run_type in (
        "DETECTION",
        "MASKED",
        "INVERTED",
        "INVMASKED",
    ):
        move_detection_outputs(path_to_unpacked)

    else:
        raise ValueError(
            f"Unknown run type {run_type}"
        )


def move_spectral_outputs(path_to_unpacked: Path) -> None:

    ascii_tarball_path = path_to_unpacked / "ascii_tarball.tar.gz"
    catalogues_path = path_to_unpacked / "catalogues"

    if ascii_tarball_path.is_file():
        shutil.move(ascii_tarball_path, TMPDIR / "ascii_tarball.tar.gz")
    if catalogues_path.is_dir():
        for path in catalogues_path.iterdir():
            if path.is_file():
                catalogues_path = DATADIR / "catalogues"
                catalogues_path.mkdir(
                    parents=True,
                    exist_ok=True,
                )
                shutil.move(path, catalogues_path)


def move_detection_outputs(path_to_unpacked):
    metadata_file = path_to_unpacked / "metadata.json"

    with open(metadata_file) as f:
        metadata = json.load(f)

    sbid = metadata["SBID"]
    run_type = metadata["RUN_TYPE"]

    target_dir = DATADIR / sbid

    target_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.move(
        path_to_unpacked / "config",
        target_dir / "config",
    )

    shutil.move(
        path_to_unpacked / "logs",
        target_dir / "logs",
    )

    if run_type == "DETECTION":
        output_name = "outputs"

    elif run_type == "INVERTED":
        output_name = "inverted_outputs"

    elif run_type == "MASKED":
        output_name = "masked_outputs"

    elif run_type == "INVMASKED":
        output_name = "inv_masked_outputs"

    shutil.move(
        path_to_unpacked / output_name,
        target_dir / output_name,
    )


def delete_local_run_outputs(paths: list[Path]) -> None:
    """Deletes local output files and directories."""
    for path in paths:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()


def run_upload(
    run_type,
    quality,
    sbid,
    temp_dir,
    parent_dir,
    db_password,
    config_file_path,
    comment
):
    """
    Runs the db upload script to load the run data & meta-data into the DB
    """
    cmd = [
        "python3",
        "database/db_upload.py",
        "-m", run_type,
        "-q", quality,
        "-s", sbid,
        "-t", temp_dir,
        "-d", parent_dir,
        "-pw", db_password,
        "-cs", config_file_path,
        "-C", comment,
    ]

    subprocess.run(
        cmd,
        check=True,
    )


def archive_remote_output(
    sftp: paramiko.SFTPClient,
    remote_tar: Path,
    archive_dir: Path,
) -> None:

    try:
        sftp.mkdir(str(archive_dir))
    except OSError:
        pass

    base = remote_tar.with_suffix("").with_suffix("")

    files_to_archive = [
        remote_tar,
        base.with_suffix(".sha256"),
        base.with_suffix(".complete"),
    ]

    for source in files_to_archive:
        destination = archive_dir / source.name
        sftp.rename(str(source), str(destination))


def main():
    """Main function"""

    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.RejectPolicy())
    client.connect(HOST, username=USERNAME)
    sftp = client.open_sftp()

    try:

        # Fetch any completed output tars
        zips = fetch_completed_outputs(client, sftp, TMPDIR, REMOTE_DIR)

        for local_zip, remote_zip in zips:
            # Unzip them
            local_unzip = unpack_outputs(local_zip, TMPDIR)

            # Figure out the run type, quality flag etc. from the run meta-data
            # file
            (run_type, sbid, quality, comment) = extract_meta_data(local_unzip)

            # Place outputs in expected locations for upload
            move_outputs_to_upload_paths(local_unzip, run_type)

            # Upload to DB
            run_upload(
                run_type,
                quality,
                sbid,
                TMPDIR,
                DATADIR,
                FLASHPASS,
                CONFIGPATH,
                comment
            )

            # Delete uploaded data products from the VM
            delete_local_run_outputs([local_unzip, local_zip])

            # Move zip to scratch uploaded_results folder on HPC
            archive_remote_output(sftp, remote_zip, REMOTE_ARCHIVE_DIR)

    finally:
        sftp.close()
        client.close()


if __name__ == "__main__":
    main()
