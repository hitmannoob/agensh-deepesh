#!/usr/bin/env python3
import os
import sys

HOOK = os.path.join(os.environ['AGENSH_ROOT'], 'tasks/software-project/hooks/sync.py')
os.execv(sys.executable, [sys.executable, HOOK])
