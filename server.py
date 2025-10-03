from lean_interact import LeanREPLConfig, LeanServer, Command, LocalProject

project = LocalProject(directory="/Users/mrmackamoo/Projects/lean-repl/repl/", lake_path="/Users/mrmackamoo/.elan/bin/lake")
config = LeanREPLConfig(project=project) # download and build Lean REPL
server = LeanServer(config) # start Lean REPL
response = server.run(Command(cmd="theorem ex (n : Nat) : n = 5 → n = 5 := id"))
print(response)