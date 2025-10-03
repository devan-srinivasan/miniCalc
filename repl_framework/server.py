import subprocess, json, os
from datetime import datetime

class State():
    """
    A state in the lean server. This is a node in the state tree.
    - env_id: the environment id of this state
    - command: the command that was sent to the lean server to reach this state
    - parent: the parent state (which will have a command here)
    - children: the child states (which will have commands here)
    - response: the json (dict) response from the lean server (if any)
    """

    def __init__(self, env_id: int, command: str, parent: 'State' = None):
        self.env_id = env_id
        self.command = command
        self.parent = parent
        self.children = []
        self.response = None

    def add_child(self, child_state):
        self.children.append(child_state)
    

class LeanServer():
    """
    Wrapper for the lean server. We can use this to manage history, states, logging, etc.
    """

    def __init__(self, logfile: str = None):
        if logfile:
            assert logfile
            self.state_tree = self.reconstruct(logfile)
        else:
            self.state_tree = []
        
        self.proc = None

        if not logfile:
            # initialize logfile as DD_MM_YYYY_HH_MM_SS_log.jsonl inside logs/ directory (created if DNE)
            os.makedirs("logs", exist_ok=True)
            self.logfile = f"logs/{datetime.now().strftime('%d_%m_%Y_%H_%M_%S')}_log.jsonl"
        else:
            self.logfile = logfile

    def reconstruct(self, logfile: str) -> list[State]:
        """
        Reconstruct the state tree from a logfile. We read each line, and combine recv and resp events
            into state objects, and then connect them sequentially into a tree which is returned
        
        Each line will be recv/resp: {json}\n where json will be a dict with key env_id to indicate the relationship
        If it's input, then it will have a cmd key, and if not ...
        """

        # initialize roots, and last_state is the previous state (parent) to create tree
        roots = []
        last_state:State = None

        # read the logfile line by line
        with open(logfile, "r") as f:
            for line in f:
                direction, json_str = line.split(": ", 1)

                try:
                    json_msg = json.loads(json_str)
                except Exception as e:
                    print(f"Malformed Input. Make sure lines were saved properly with log(). Error when decoding json: {e}")
                    if not last_state:
                        continue
                    else:
                        print("Cannot continue, sequence is broken.")
                        raise e

                if direction == "recv":

                    assert "cmd" in json_msg, "Malformed Input. Received message without cmd key."
                    
                    # on receives, we always start a state
                    new_state = State(
                        command=json_msg["cmd"],
                    )
                    
                    # if an environment was passed, currently we only support that the previous state is the parent
                    if "env_id" in json_msg:
                        assert last_state and last_state.env_id == json_msg["env_id"], "Mismatched env_id in log reconstruction"
                        last_state.add_child(new_state)
                        new_state.parent = last_state

                    # else we are starting a new root
                    else:
                        roots.append(new_state) # new root state
                    
                    last_state = new_state
                    
                elif direction == "resp":
                    # just copy the response, and the returned id represents this state
                    last_state.response = json_msg
                    last_state.env_id = json_msg["env_id"]

        return roots
        

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

    def send(self, command, state: State = None):
        """
        Send a command to the lean server. If state is None, then a new state is created
        """
        json_msg = {
            "cmd": command,
        }

        json_msg_str = json.dumps(json_msg)

        if state:
            json_msg["env_id"] = state.env_id

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
        child = State(
            env_id=response["env_id"], 
            command=command, 
            parent=state,
            response=response
        )

        if state:
            state.add_child(child)          # extend existing state
        else:
            self.state_tree.append(child)   # new root state

        return child
    
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