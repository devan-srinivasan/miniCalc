import os
from lean_interact import LeanREPLConfig, LeanServer, Command, LocalProject, AutoLeanServer
from datetime import datetime
from tqdm import tqdm

project = LocalProject(directory="./leanCalc/", lake_path="/Users/mrmackamoo/.elan/bin/lake")
config = LeanREPLConfig(project=project) # download and build Lean REPL
server = AutoLeanServer(config) # start Lean REPL

class Prover:
  """
  This is a simple abstract base class for a theorem prover that each LLM will implement
  """
  def __init__(self, name: str):
    self.name = name
  def prove(self, theorem: str) -> str:
    raise NotImplementedError("Prover is an abstract base class") 
  

def evaluate(
  prover: Prover, 
  dataset: list[str],
  max_retries: int = 1,
  resume: bool = False,
  log_file: str = None
):
  """
  This function standardizes how we evaluate LLMs on lean problems. The underlying 
  proving method it so be implemented by each LLM, but this will handle all the logging, 
  and metrics in one place.
  
  It will log all results to logs/name/dd_mm_yyyy_hh_mm_ss.txt

  We assume each str in dataset includes the header and theorem!
  """
  # intialize logging directory
  log_dir = f"logs/{prover.name}/"
  os.makedirs(log_dir, exist_ok=True)

  processed_ids = set()

  if resume:
    assert log_file

    with open(log_file, "r") as f:
      for line in f:
        if line.startswith("response"):
          processed_ids.add(int(line.split(".")[0][len("response "):]))
  else:
    log_file = log_dir + f"{datetime.now().strftime('%d_%m_%Y_%H_%M_%S')}.txt"

  # initialize lean server
  server.start()

  with open(log_file, "a") as f:
    for i, theorem in tqdm(enumerate(dataset)):
      if i in processed_ids:
        continue

      f.write(f"{i}: {theorem}\n")

      proven = False
      for retry in range(max_retries):
        if proven: continue

        proof = prover.prove(theorem)
        f.write(f"attempt {i}.{retry+1}:{proof}\n")

        # check with lean server
        lean_code = f"{theorem}\n{proof}"

        response = server.run(Command(cmd=lean_code))
        f.write(f"response {i}.{retry+1}: {response}\n")

        # parse lean response as success / failure
        if any('no goals' in msg.data for msg in response.messages) and len(response.messages) == 1:
          proven = True
        else:
          proven = False

        f.write(f"response {i}.{retry+1}: {proven}\n")

class DumProver(Prover):
  def __init__(self):
    super().__init__(name="DumProver")
  
  def prove(self, theorem: str) -> str:
    return "bobby"  # always fails
  
dataset = ["example (a b : Nat) : a + b = b + a := by "] * 1000

evaluate(
  prover=DumProver(),
  dataset=dataset,
  max_retries=1,
  resume=False,
)