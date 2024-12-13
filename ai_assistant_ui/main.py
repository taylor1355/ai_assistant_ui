from textual.app import App
from textual.widgets import DataTable

class InboxApp(App):
    """A minimal app showing a DataTable widget."""

    def compose(self):
        # Create and yield the DataTable widget
        yield DataTable()

    def on_mount(self):
        # Get reference to the DataTable widget
        table = self.query_one(DataTable)
        
        # Add columns
        table.add_columns("Name", "Value")
        
        # Add some dummy data
        table.add_rows([
            ("Alice", "123"),
            ("Bob", "456"),
            ("Carol", "789"),
        ])

if __name__ == "__main__":
    app = InboxApp()
    app.run()