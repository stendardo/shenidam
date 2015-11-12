import sys;
with open(sys.argv[1],'rb') as f:
	data = f.read().encode('base64')
sys.stdout.write(data)