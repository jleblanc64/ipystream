import ipystream

# ps auxww | grep my-tag
ipystream.run(MAX_KERNELS=3, debug=True, tag="my-tag")
