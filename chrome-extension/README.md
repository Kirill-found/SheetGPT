# SheetGPT Chrome Extension

AI-powered assistant for Google Sheets - analyze data, create formulas, and generate insights.

## 🎨 Design System

**v2.0 - Neo-Brutalist Design**

- **Fonts**: JetBrains Mono (headings, UI) + Inter (body text)
- **Themes**: Dark (default) + Light
- **Accent**: Lime `#A1FF62` (dark) / Purple `#6840FF` (light)
- **Style**: Hard shadows, grid background, sharp corners

## 🚀 Features

- **AI Chat Interface** - sidebar with chat for data analysis
- **Auto Data Reading** - automatically reads data from active sheet
- **Smart Analysis** - top products, averages, filtering
- **Table Generation** - create tables from AI knowledge
- **Row Highlighting** - highlight rows based on conditions
- **Formula Generation** - SUMIF, VLOOKUP, and more

## 📦 Installation

1. Open Chrome: `chrome://extensions/`
2. Enable "Developer mode" (toggle in top right)
3. Click "Load unpacked"
4. Select the `chrome-extension` folder
5. Done!

## 🔧 How to Use

1. Open any Google Sheets document
2. Click the blue button on the right (or extension icon)
3. Sidebar opens on the right
4. Select data (or leave empty for AI generation)
5. Ask your question in chat
6. Get results!

## 📝 Example Queries

### With data:
- "Find top 3 products by sales"
- "Calculate average revenue"
- "Highlight rows where amount < 100000"
- "Merge first and last name columns"

### Without data (AI generation):
- "Create a table of European countries with population"
- "List of largest Russian cities"
- "Planets of the solar system"

## 🔑 OAuth Setup

See [SETUP_OAUTH.md](SETUP_OAUTH.md) for Google Sheets API configuration.

## 🔗 API Backend

- **Production:** https://sheetgpt-production.up.railway.app
- **Endpoint:** /api/v1/formula

## 📄 License

MIT License
