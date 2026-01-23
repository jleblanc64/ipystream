from ipystream.voila import run_raw

print("http://localhost:8866?tok=a")
print("http://localhost:8866?tok=b")
print("http://localhost:8866?tok=c")
print("http://localhost:8866?tok=d")

run_raw.run(enforce_PARAM_KEY_TOKEN=True, token_to_user_fun=lambda x: x)
