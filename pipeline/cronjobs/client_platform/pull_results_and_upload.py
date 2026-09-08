"""
Push Detection to Oracle & Push Spectral to Oracle are modified to move all
relevant files for a run into a folder, make a metadata.txt containing the
run info such as sbid, quality_flag, run type etc., zip it into a single zip
for transfer, move it into the transfer folder and mark it as complete
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
REMOTE_DIR = Path(os.environ['HPC_SCRATCH'] / "outputs_to_transfer")
REMOTE_ARCHIVE_DIR = Path(os.environ['HPC_SCRATCH'] / "uploaded_outputs")
TMPDIR = Path(os.environ['TMPDIR'])
DATADIR = Path(os.environ['DATA'])
CONFIGPATH = "config"
FLASHPASS = str(os.environ['FLASHPASS'])
CLIENT = paramiko.SSHClient()
CLIENT.load_system_host_keys()
CLIENT.set_missing_host_key_policy(paramiko.RejectPolicy())
CLIENT.connect(HOST, username=USERNAME)
SFTP = CLIENT.open_sftp()


class RunType(Enum):
    """Controls the run types allowed, should probably be used everywhere but
    its needed here and much of the codebase is bash"""
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
    client: paramiko.SSHClient,
    sftp: paramiko.SFTPClient,
    local_dir: Path,
    remote_dir: Path,
) -> List[Path]:
    """ Copies all outputs from linefinder runs to local VM"""

    local_zips = []
    try:

        entries = sftp.listdir_attr(str(remote_dir))

        completed_outputs = sorted(
            remote_dir / (entry.filename.removesuffix(".complete") + ".tar.gz")
            for entry in entries
            if entry.filename.endswith(".complete")
        )

        # Foreach completed run outputs tar
        print(f"Found {len(completed_outputs)} outputs to transfer:")
        for remote_path in completed_outputs:
            print(remote_path)
            # Make Remote Hash
            stdin, stdout, _ = client.exec_command(
                f"sha256sum '{remote_path}'"
            )
            remote_hash = stdout.readline().split()[0]

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

            local_zips.append(local_path)

    finally:
        sftp.close()
        client.close()

    return local_zips


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


def move_outputs_to_upload_paths(path_to_unpacked: Path) -> None:
    """The DB upload script expects the outputs to be in specific locations,
     this function moves the various parts of the unpacked tars contents to the 
     various locations they need to be at.
     """

    ascii_tarball_path = path_to_unpacked / "ascii_tarball.tar.gz"
    catalogues_path = path_to_unpacked / "catalogues"

    if ascii_tarball_path.is_file():
        shutil.move(ascii_tarball_path, TMPDIR / "ascii_tarball.tar.gz")
    if catalogues_path.is_dir():
        for path in catalogues_path.iterdir():
            if path.is_file():
                catalogues_path = DATADIR / "catalogues"
                catalogues_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(path, catalogues_path)


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
    remote_file: Path,
    archive_dir: Path,
) -> None:
    """Moves remote output files into an archive directory."""

    try:
        sftp.mkdir(str(archive_dir))
    except OSError:
        # Already exists
        pass

    destination = archive_dir / remote_file.name
    sftp.rename(
        str(remote_file),
        str(destination),
    )


def main():
    """Main function"""
    # Fetch any completed output tars
    local_zips = fetch_completed_outputs(CLIENT, SFTP, TMPDIR, REMOTE_DIR)

    for local_zip in local_zips:
        # Unzip them
        local_unzip = unpack_outputs(local_zip, TMPDIR)

        # Figure out the run type, quality flag etc. from the run meta-data
        # file
        (run_type, sbid, quality, comment) = extract_meta_data(local_unzip)

        # Place outputs in expected locations for upload
        move_outputs_to_upload_paths(local_unzip)

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
        archive_remote_output(SFTP, local_unzip, REMOTE_ARCHIVE_DIR)


if __name__ == "__main__":
    main()
