import logging
import re
from rich.console import Console
from src.utils import (
    COLOR_ERROR,
    COLOR_PRIMARY,
    COLOR_SECONDARY,
    COLOR_YELLOW,
    COLOR_HIGHLIGHT,
    COLOR_ACCENT,
)

console = Console()


def generate_response_time_chart(results):
    
    labels = []
    data = []
    for _, message in results:
        host = message.split("] ")[1].split(" ")[0]
        match = re.search(r"Response: ([\d.]+) ms", message)
        if match:
            labels.append(host)
            data.append(float(match.group(1)))
    if not data:
        logging.warning("No valid response times for chart")
        console.print(f"[{COLOR_ERROR}][Error] No valid response times to display![/]")
        return False

    try:
        max_bar_length = 50
        scale_factor = 10
        max_response = max(data, default=1)
        max_label_length = max(len(label) for label in labels)

        console.print(
            f"[{COLOR_SECONDARY}]┌"
            + "─" * (max_label_length + max_bar_length + 15)
            + "┐[/]"
        )
        console.print(
            f"[{COLOR_SECONDARY}]│ Response Time Chart (1 █ = 10 ms, Max: {max_response:.2f} ms) │[/]"
        )
        console.print(
            f"[{COLOR_SECONDARY}]├"
            + "─" * (max_label_length + max_bar_length + 15)
            + "┤[/]"
        )

        colors = [
            COLOR_ERROR,
            COLOR_PRIMARY,
            COLOR_SECONDARY,
            COLOR_YELLOW,
            COLOR_HIGHLIGHT,
        ]
        for i, (label, response_time) in enumerate(zip(labels, data)):
            bar_length = int(response_time / scale_factor)
            if bar_length > max_bar_length:
                bar_length = max_bar_length
            bar = "█" * bar_length
            console.print(
                f"[{COLOR_SECONDARY}]│ [{COLOR_ACCENT}]{label:<{max_label_length}}[/] | [{colors[i % len(colors)]}]{bar:<{max_bar_length}}[/] {response_time:.2f} ms [{COLOR_SECONDARY}]│[/]"
            )

        console.print(
            f"[{COLOR_SECONDARY}]└"
            + "─" * (max_label_length + max_bar_length + 15)
            + "┘[/]"
        )
        console.print(f"[{COLOR_PRIMARY}]Scale: █ = 10 ms[/]")

        
        return True
    except Exception as e:
        logging.error(f"Failed to generate ASCII chart: {str(e)}")
        console.print(
            f"[{COLOR_ERROR}][Error] Failed to generate ASCII chart: {str(e)}[/]"
        )
        return False
