import sys, os
with open(r'D:\LiveCode\PadhaiWithAIWithclaude03022026\iis_test.txt', 'w') as f:
    f.write('Python is running under IIS!\n')
    f.write('Executable: ' + sys.executable + '\n')
    f.write('Working dir: ' + os.getcwd() + '\n')
    f.write('Env vars:\n')
    for k, v in sorted(os.environ.items()):
        f.write(f'  {k}={v}\n')
