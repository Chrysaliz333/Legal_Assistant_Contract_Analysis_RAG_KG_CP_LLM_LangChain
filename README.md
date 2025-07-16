# Legal Assistant Contract Analysis

A comprehensive AI-powered legal contract analysis system using OpenAI GPT-4o-mini, LangChain, and NetworkX for intelligent legal document review and risk assessment.

## 🎯 Features

- **AI-Powered Analysis**: Uses OpenAI GPT-4o-mini for cost-effective and accurate legal contract analysis
- **Knowledge Graph Visualization**: Interactive visualization of legal concept relationships using NetworkX
- **Constraint Validation**: Comprehensive legal constraint checking with jurisdiction-specific rules
- **Multi-Focus Analysis**: Analyze contracts across key areas (confidentiality, liability, IP, termination)
- **Risk Assessment**: Automated risk scoring and recommendations
- **Document Retrieval**: Integration with Tavily AI for legal research and precedent finding
- **Cost Optimization**: Intelligent analysis depth adjustment based on contract complexity

## 📋 Requirements

- Python 3.10.11+
- OpenAI API key
- Tavily AI API key
- Jupyter Notebook environment

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/skkuhg/Legal_Assistant_Contract_Analysis_RAG_KG_CP_LLM_LangChain.git
cd legal-assistant-contract-analysis
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Up Environment Variables

Create a `.env` file in the root directory:

```env
OPENAI_API_KEY=your-openai-api-key-here
TAVILY_API_KEY=your-tavily-api-key-here
```

### 4. Run the Notebook

```bash
jupyter notebook Legal_Assistant_Contract_Analysis.ipynb
```

## 📊 Usage Examples

### Basic Contract Analysis

```python
# Analyze a contract with default focus areas
results = pipeline.analyze_contract(
    contract_text=your_contract_text,
    focus_areas=['confidentiality', 'liability', 'termination'],
    show_knowledge_graph=True
)
```

### Knowledge Graph Exploration

```python
# Explore specific legal concepts
show_knowledge_graph_for_concept('confidentiality')
show_knowledge_graph_for_concept('intellectual_property')
```

### Optimized Analysis for Different Contract Sizes

The system automatically adjusts analysis depth based on contract complexity:

- **Short contracts (0-500 words)**: Comprehensive analysis (~$0.10-0.14)
- **Medium contracts (500-1000 words)**: Standard analysis (~$0.12-0.18)
- **Large contracts (1000+ words)**: Focused analysis (~$0.15-0.23)

## 🏗️ Architecture

### Core Components

1. **LegalDocumentRetriever**: Tavily AI-powered legal research and document retrieval
2. **LegalKnowledgeGraph**: NetworkX-based legal concept relationship modeling
3. **LegalConstraintParser**: Comprehensive legal validation with jurisdiction rules
4. **ContractAnalysisPipeline**: Orchestrates complete analysis workflow

### Analysis Pipeline

```
Contract Input → Knowledge Graph Visualization → AI Analysis → Constraint Validation → Risk Assessment → Comprehensive Report
```

## 📈 Knowledge Graph

The system includes a comprehensive legal knowledge graph with:

- **91 legal concepts** covering contract law fundamentals
- **Primary legal areas**: Confidentiality, Liability, IP, Termination
- **Requirements & obligations**: Notice requirements, defense obligations
- **Related concepts**: Jurisdiction-specific rules, enforcement mechanisms

## ⚖️ Legal Disclaimer

This tool provides AI-powered legal analysis for informational purposes only. It should not replace professional legal advice. Always consult qualified legal counsel for important legal decisions.

## 🔧 Configuration

### GPT-4o-mini Settings

```python
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.3,      # Consistent legal analysis
    max_tokens=2000,      # Sufficient for detailed responses
    timeout=30,           # Efficient processing
    max_retries=2         # Reliable operation
)
```

### Supported Focus Areas

- Confidentiality & Non-disclosure
- Liability & Risk allocation
- Intellectual Property rights
- Termination clauses
- Force Majeure provisions
- Dispute Resolution mechanisms
- Governing Law & Jurisdiction

## 📝 Development

### Project Structure

```
legal-assistant-contract-analysis/
├── Legal_Assistant_Contract_Analysis.ipynb  # Main notebook
├── README.md                                # This file
├── requirements.txt                         # Python dependencies
├── .env.example                            # Environment variables template
├── .gitignore                              # Git ignore rules
├── LICENSE                                 # MIT License

```

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- OpenAI for GPT-4o-mini API
- LangChain for AI framework
- Tavily AI for legal document retrieval
- NetworkX for graph visualization
- The open-source community for various Python libraries

## 📞 Support

For questions or support, please open an issue on GitHub or contact the development team.

---

**Built with ❤️ for the legal technology community**
