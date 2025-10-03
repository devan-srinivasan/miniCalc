import subprocess, json, os
from datetime import datetime

class LeanServer():
    """
    Wrapper for the lean server. We can use this to manage history, states, logging, etc.
    """

    def __init__(self, logfile: str = None):
        self.state_tree = []
        
        self.proc = None

        if not logfile:
            # initialize logfile as DD_MM_YYYY_HH_MM_SS_log.jsonl inside logs/ directory (created if DNE)
            os.makedirs("logs", exist_ok=True)
            self.logfile = f"logs/{datetime.now().strftime('%d_%m_%Y_%H_%M_%S')}_log.jsonl"
        else:
            self.logfile = logfile
  
    def start(self, repl_path: str = None):
        """
        Start the lean server. Open a process and run `lake exe repl`
        repl_path: the path to the lean project. If None, then we use the current directory.
        """
        self.proc = subprocess.Popen(
            ["lake", "exe", "repl"], 
            cwd=repl_path,
            stdin=subprocess.PIPE, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )

    def send(self, command, env_id: int = None):
        """
        Send a command to the lean server. If state is None, then a new state is created
        """
        json_msg = {
            "cmd": command,
        }

        json_msg_str = json.dumps(json_msg)

        if env_id:
            json_msg["env_id"] = env_id

        # we send the command through stdin
        self.proc.stdin.write(json_msg_str + "\n")
        self.proc.stdin.flush()

        # log request
        self.log(json_msg_str, inbound=True)

        # this will block until we get a response
        response_str = self.proc.stdout.readline()
        response = json.loads(response_str)

        # log response
        self.log(response_str, inbound=False)

        # update the state tree
        return response, env_id

    def log(self, message: str, inbound: bool = True):
        """
        Log all server interactions
        - message: already formatted into a string
        """
        with open(self.logfile, "a") as f:
            f.write(f"{'recv' if inbound else 'resp'}: " + message + "\n")

    def kill(self):
        """
        Kill the lean server
        """
        assert self.proc is not None, "Lean repl server is not running"
        self.proc.terminate()
        self.proc.wait()