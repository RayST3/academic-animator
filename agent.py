from agno.agent import Agent
from agno.models.google import Gemini
from agno.tools.websearch import WebSearchTools
search_agent=Agent(model=Gemini("gemini-3.1-flash-lite"),
                   instructions="you are agent that searches web for news and writes poems about the news",
                   tools=[WebSearchTools()])
search_agent.print_response("Search Delhi Jantar Mantar news")
#print(result.content)