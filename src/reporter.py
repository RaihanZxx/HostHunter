"""
reporter.py - Provides reporting and visualization functionalities for HostHunter.

This module is responsible for generating visual representations of host check results,
such as an ASCII-based response time chart, to help users quickly understand
the performance characteristics of checked hosts.
"""

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
    """
    Generates and displays an ASCII-based bar chart of host response times.

    Parses hostnames and their corresponding response times from the provided
    results list and visualizes them as a bar chart in the console.

    Args:
        results (list): A list of tuples, where each tuple contains (color, message)
                        from host check operations. The message is expected to contain
                        response time information.

    Returns:
        bool: True if the chart was generated successfully, False otherwise.
    """
    labels = []  # To store hostnames
    data = []    # To store response times

    # Parse host and response time from each result message
    for _, message in results:
        # Extract host from message (assuming format like "[Status] Host (IP: ..., Response: ... ms)")
        host_match = re.search(r"] (.*?) \(IP:", message)
        host = host_match.group(1) if host_match else "Unknown Host"

        # Extract response time using regex
        match = re.search(r"Response: ([\d.]+) ms", message)
        if match:
            labels.append(host)
            data.append(float(match.group(1)))

    if not data:
        logging.warning("No valid response times for chart")
        console.print(f"[{COLOR_ERROR}][Error] No valid response times to display![/]")
        return False

    try:
        max_bar_length = 50  # Maximum length of the ASCII bar
        scale_factor = 10    # 1 '█' represents 10 ms
        max_response = max(data, default=1) # Get the maximum response time for scaling
        max_label_length = max(len(label) for label in labels) # Determine max label width for alignment

        # Print chart header
        console.print(
            f"[{COLOR_SECONDARY}]┌" 
            + "─" * (max_label_length + max_bar_length + 15) 
            + "┐[/]"
        )
        console.print(
            f"[{COLOR_SECONDARY}]│ Response Time Chart (1 █ = {scale_factor} ms, Max: {max_response:.2f} ms) │[/]"
        )
        console.print(
            f"[{COLOR_SECONDARY}]├" 
            + "─" * (max_label_length + max_bar_length + 15) 
            + "┤[/]"
        )

        # Define a list of colors for cycling through bars
        colors = [
            COLOR_ERROR,
            COLOR_PRIMARY,
            COLOR_SECONDARY,
            COLOR_YELLOW,
            COLOR_HIGHLIGHT,
        ]
        # Iterate through labels and data to print each bar
        for i, (label, response_time) in enumerate(zip(labels, data)):
            # Calculate bar length based on response time and scale factor
            bar_length = int(response_time / scale_factor)
            # Cap bar length at max_bar_length
            if bar_length > max_bar_length:
                bar_length = max_bar_length
            bar = "█" * bar_length # Create the ASCII bar

            # Print each row of the chart with formatted label, bar, and response time
            console.print(
                f"[{COLOR_SECONDARY}]│ [{COLOR_ACCENT}]{label:<{max_label_length}}[/] | [{colors[i % len(colors)]}]{bar:<{max_bar_length}}[/] {response_time:.2f} ms [{COLOR_SECONDARY}]│[/]"
            )

        # Print chart footer
        console.print(
            f"[{COLOR_SECONDARY}]└" 
            + "─" * (max_label_length + max_bar_length + 15) 
            + "┘[/]"
        )
        console.print(f"[{COLOR_PRIMARY}]Scale: █ = {scale_factor} ms[/]")

        return True
    except Exception as e:
        logging.error(f"Failed to generate ASCII chart: {str(e)}")
        console.print(
            f"[{COLOR_ERROR}][Error] Failed to generate ASCII chart: {str(e)}[/]"
        )
        return False
