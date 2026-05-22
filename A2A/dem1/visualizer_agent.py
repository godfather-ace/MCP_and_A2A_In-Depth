import requests
import plotly.graph_objects as go

class A2AVisualiser:
    def __init__(self, name="Visualiser"):
        self.name = name
        self.analyst_url = "http://localhost:8001/execute"

    def get_analysis(self, prompt):
        print(f"[{self.name}] Calling CrewAI Analyst via A2A...")
        payload = {"input": prompt}
        try:
            response = requests.post(self.analyst_url, json=payload)
            return response.json().get("output", "")
        except Exception as e:
            return f"Error: {e}"

    def create_visualization(self, analysis_text):
        print(f"[{self.name}] Generating Interactive Chart...")
        
        # Mocking data points based on typical AI growth trends for 2024-2026
        years = ['2024', '2025', '2026 (Projected)']
        adoption_rate = [45, 70, 95]  # Expansion trend
        model_complexity = [30, 65, 90] # Sophistication trend
        
        fig = go.Figure()
        
        # Add Adoption Trend
        fig.add_trace(go.Scatter(
            x=years, y=adoption_rate, fill='tozeroy',
            name='Industry Adoption (%)', line_color='indigo'
        ))
        
        # Add Model Complexity Trend
        fig.add_trace(go.Scatter(
            x=years, y=model_complexity, fill='tonexty',
            name='Model Sophistication', line_color='cyan'
        ))

        fig.update_layout(
            title="Generative AI Evolution Analysis (A2A Protocol Output)",
            xaxis_title="Year",
            yaxis_title="Growth Score",
            template="plotly_dark"
        )
        
        # This will open a browser window with your chart
        fig.show()

    def run(self, topic):
        # 1. Get the raw analysis from the other agent
        analysis_data = self.get_analysis(topic)
        print(f"\n--- Analyst Report ---\n{analysis_data}\n")
        
        # 2. Transform that report into a visual
        self.create_visualization(analysis_data)

if __name__ == "__main__":
    visualiser = A2AVisualiser()
    visualiser.run("Analyze the growth of Generative AI in 2025.")