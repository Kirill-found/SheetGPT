# Fix stackedType - only add for charts that support it
file_path = 'C:/Projects/SheetGPT/chrome-extension/src/sheets-api.js'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

old = """          domains: [domain],
          series: series,
          headerCount: 1,
          stackedType: 'NOT_STACKED'
        }
      };

      // interpolateNulls only supported for LINE, AREA, SCATTER
      if (['LINE', 'AREA', 'SCATTER'].includes(googleChartType)) {
        spec.basicChart.interpolateNulls = true;
      }

      // For scatter, add specific settings
      if (googleChartType === 'SCATTER') {
        spec.basicChart.lineSmoothing = false;
      }

      // For area chart, stack if multiple series
      if (googleChartType === 'AREA' && series.length > 1) {
        spec.basicChart.stackedType = 'STACKED';
      }"""

new = """          domains: [domain],
          series: series,
          headerCount: 1
        }
      };

      // stackedType only supported for BAR, COLUMN, AREA (NOT for LINE, SCATTER)
      if (['BAR', 'COLUMN', 'AREA'].includes(googleChartType)) {
        spec.basicChart.stackedType = 'NOT_STACKED';
      }

      // interpolateNulls only supported for LINE, AREA, SCATTER
      if (['LINE', 'AREA', 'SCATTER'].includes(googleChartType)) {
        spec.basicChart.interpolateNulls = true;
      }

      // For scatter, add specific settings
      if (googleChartType === 'SCATTER') {
        spec.basicChart.lineSmoothing = false;
      }

      // For area chart, stack if multiple series
      if (googleChartType === 'AREA' && series.length > 1) {
        spec.basicChart.stackedType = 'STACKED';
      }"""

if old in content:
    content = content.replace(old, new)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: Fixed stackedType')
else:
    print('ERROR: Pattern not found')
