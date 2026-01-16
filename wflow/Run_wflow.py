import subprocess

def run_wflow(
    wflow_path,
    num_threads
):
    '''
    Definition:
        Function to run wflow model
    References:
        https://deltares.github.io/Wflow.jl/v0.8/user_guide/additional_options/
    Arguments:
        wflow_path (str):
            Path to folder that stores all necessary files to run wflow model
        num_threads (int):
            Number of threads that controls how fast the wflow model can run
    '''

    # Build the Julia command
    cmd = [
        "julia",
        "-t", f"{num_threads}",
        "-e",
        f'cd("{wflow_path}"); using Wflow; Wflow.run("wflow_sbm.toml")'
    ]

    # Run the command and write output to log
    with open(fr"{wflow_path}\wflow_run.log", "w") as f:
        process = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, text=True)

    print(f"Wflow run completed. Log saved to wflow_run.log")
