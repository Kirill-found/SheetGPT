#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import sys

data = json.load(sys.stdin)
print('=' * 60)
print('TEST: RED COLOR DETECTION FOR SHILOV')
print('=' * 60)
print(f"action_type: {data.get('action_type')}")
print(f"highlight_rows: {data.get('highlight_rows')}")
print(f"highlight_color: {data.get('highlight_color')}")
print(f"highlight_message: {data.get('highlight_message')}")
print('=' * 60)

expected_color = '#FF6B6B'
actual_color = data.get('highlight_color')
actual_rows = data.get('highlight_rows')

if actual_rows == [10] and actual_color == expected_color:
    print('[SUCCESS] RED COLOR DETECTION WORKS PERFECTLY!')
    print(f'Row 10 (Shilov) highlighted with RED {expected_color}')
elif actual_rows == [10] and actual_color != expected_color:
    print('[PARTIAL] Row is correct but COLOR is WRONG')
    print(f'Expected color: {expected_color} (RED)')
    print(f'Actual color: {actual_color}')
else:
    print('[FAILED] Both row and color are wrong')
    print(f'Expected: row 10 with {expected_color}')
    print(f'Actual: rows {actual_rows} with {actual_color}')
