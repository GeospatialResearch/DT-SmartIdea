import subprocess


def generate_wflow_files(
    folder_path,
    subbasin,
    strord,
    bbox
):
    '''
    Definition:
        Function to generate necessary files for Wflow model
    References:
        https://deltares.github.io/hydromt_wflow/stable/_examples/build_sediment.html
    Arguments:
        folder_path (str):
            Path to folder that contains wflow_build.yml, data_catalog.yml,
            and a folder that contains all necessary files
        subbasin (list):
            Outlet coordinates
        strord (int):
            Minimum stream order
        bbox (list):
            Given bounding box coordinates that contains the subbasin coordinates
    '''

    cmd = [
        "hydromt", "build", "wflow",
        f"{folder_path}/wflow_test_full",
        "-r", f"{f'subbasin': {subbasin}, 'strord': {strord}, 'bbox': {bbox}}",
        "-i", f"{folder_path}/wflow_build.yml",
        "-d", f"{folder_path}/data_catalog.yml",
        "-vv"
    ]

    # Run and print live output
    subprocess.run(cmd, check=True)