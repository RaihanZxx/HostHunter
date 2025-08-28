"""
cli.py - Main Command-Line Interface for HostHunter.

This module provides the interactive command-line interface for the HostHunter tool,
allowing users to perform various network checks, scan hosts from files, save results,
and visualize response times. It handles user input, displays information, and
orchestrates calls to other modules for core functionalities.
"""

import os
import logging
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from rich.panel import Panel
from rich.text import Text

# Internal module imports for HostHunter functionalities
from src import utils
from src import host_checker
from src.file_handler import scan_hosts_from_file, save_results
from src import reporter
from src.special_checks import SPECIAL_CHECKS
from src.utils import (
    COLOR_ERROR,
    COLOR_PRIMARY,
    COLOR_SECONDARY,
    COLOR_WARNING,
    PANEL_BORDER_COLOR,
    COLOR_CYAN,
)


console = Console()


def main_menu():
    """
    Displays the main interactive menu for HostHunter and handles user input.

    This function runs in a loop, presenting various options to the user,
    such as checking single hosts, scanning from files, saving results,
    and performing special checks. It loads configuration, sets up logging,
    and manages the flow of the application based on user choices.
    """
    config = utils.load_config()  # Load application configuration
    utils.setup_logging(config)  # Initialize logging based on configuration
    if not utils.check_dependencies():
        console.print(
            f"[{COLOR_ERROR}][Exit] Please install missing dependencies and try again.[/]"
        )
        return

    results = []  # List to store results of host checks (color, message)

    while True:
        console.clear()  # Clear the console for a fresh menu display
        utils.print_banner()  # Display the HostHunter ASCII banner

        # Panel displaying usage instructions for the tool
        usage_text = """
- Enter a valid domain (e.g., cdn.udemy.com) for host checks.
- For file scans, provide a text file with one host per line in the 'data/hosts' folder.
- Vmess/Trojan checks require valid UUID/Password and path.
- Quota bug checks test notregular-to-regular quota exploits.
        """
        console.print(
            Panel(
                f"[{COLOR_PRIMARY}]{usage_text.strip()}[/]",
                title=Text("Usage", style=COLOR_CYAN),
                title_align="left",
                border_style=PANEL_BORDER_COLOR,
            )
        )

        # Warning panel regarding unauthorized use
        warning_text = f"[{COLOR_WARNING}]Unauthorized use of this tool for quota exploitation may violate laws or service policies. Use only with explicit permission.[/]"
        console.print(
            Panel(
                warning_text,
                title=Text("WARNING", style=COLOR_ERROR),
                title_align="left",
                border_style=PANEL_BORDER_COLOR,
            )
        )

        # Define static menu options
        menu_options = {
            "1": "Check Single Host",
            "2": "Check Ping",
            "3": "Scan Hosts from File",
            "4": "Save Results",
            "5": "Show Response Time Chart",
        }

        # Dynamically add special checks from SPECIAL_CHECKS to the menu
        special_check_start_num = len(menu_options) + 1
        special_check_choices = []
        for i, (name, check_info) in enumerate(SPECIAL_CHECKS.items()):
            option_num = str(special_check_start_num + i)
            menu_options[option_num] = f"Check {name}"
            special_check_choices.append(option_num)

        # Add Exit option dynamically at the end of the menu
        menu_options[str(len(menu_options) + 1)] = "Exit"

        console.print(f"[{COLOR_CYAN}]type help for more information[/]")
        console.print()

        # Prompt user for their choice
        choice = Prompt.ask(f"╭─HostHunter──[[{COLOR_ERROR}]Error[/{COLOR_ERROR}]]\n╰─#")

        # Handle timeout prompt for relevant choices that involve network operations
        if (
            choice in ["1", "2", "3"] + special_check_choices
        ):  # Include dynamic special check choices
            timeout = Prompt.ask(
                f"[{COLOR_PRIMARY}]Enter timeout second default:[/]",
                default=config["General"]["default_timeout"],
            )
            # Validate timeout input
            if not timeout.isdigit() or int(timeout) <= 0:
                console.print(
                    f"[{COLOR_ERROR}][Error] Timeout must be a positive integer![/]"
                )
                timeout = int(config["General"]["default_timeout"])  # Revert to default on invalid input
            else:
                timeout = int(timeout)

        # --- Menu Choice Handling ---

        if choice == "1":  # Check Single Host
            host = Prompt.ask(f"[{COLOR_PRIMARY}]Enter host (e.g., cdn.udemy.com)[/]")
            port = Prompt.ask(f"[{COLOR_PRIMARY}]Enter port default:[/]", default="443")
            # Validate host and port
            if utils.validate_host(host) and port.isdigit() and int(port) > 0:
                with console.status(f"[{COLOR_PRIMARY}]Checking {host}...", spinner="dots"):
                    color, message = host_checker.check_host(host, int(port), timeout)
                console.print(f"[{color}]{message}[/{color}]")
                results.append((color, message))
            else:
                console.print(
                    f"[{COLOR_ERROR}][Error] Invalid host or port format! Port must be a positive integer.[/]"
                )

        elif choice == "2":  # Check Ping
            host = Prompt.ask(
                f"[{COLOR_PRIMARY}]Enter host to ping (e.g., cdn.udemy.com)[/]"
            )
            # Validate host
            if utils.validate_host(host):
                with console.status(f"[{COLOR_PRIMARY}]Pinging {host}...", spinner="dots"):
                    color, message = host_checker.check_ping(host, timeout)
                console.print(f"[{color}]{message}[/{color}]")
                results.append((color, message))
            else:
                console.print(f"[{COLOR_ERROR}][Error] Invalid host format![/]")

        elif choice == "3":  # Scan Hosts from File
            file_name = Prompt.ask(
                f"[{COLOR_PRIMARY}]Enter host file name in hosts folder (e.g., hosts.txt)[/]"
            )
            # Construct absolute file path
            file_path = os.path.join(config["Paths"]["hosts_dir"], file_name)
            file_path = os.path.abspath(file_path)
            if os.path.exists(file_path):
                max_workers = int(config["General"]["max_concurrent_checks"])
                with console.status(f"[{COLOR_PRIMARY}]Scanning hosts from {file_name}...", spinner="dots"):
                    # Extend results with those from file scan
                    results.extend(scan_hosts_from_file(file_path, timeout, max_workers))
                if results:
                    # Display results in a table
                    table = Table()
                    table.add_column("Host", style=COLOR_PRIMARY)
                    table.add_column("Status", style=COLOR_SECONDARY)
                    for color, message in results:
                        # This parsing logic is fragile and should be improved for structured data
                        # For now, keeping it as is to match existing behavior
                        try:
                            host_part = message.split("] ")[1].split(" ")[0]
                            status_part = message.split("] ")[1]
                            table.add_row(
                                host_part, f"[{color}]{status_part}[/{color}]"
                            )
                        except IndexError:
                            table.add_row("N/A", f"[{color}]{message}[/{color}]")
                    console.print(table)
            else:
                console.print(f"[{COLOR_ERROR}][Error] File {file_path} not found![/]")

        elif choice == "4":  # Save Results
            if results:
                output_format = Prompt.ask(
                    f"[{COLOR_PRIMARY}]Select output format[/]",
                    choices=["txt", "json", "csv"],
                    default="txt",
                )
                save_results(results, config["Paths"]["results_dir"], output_format)
            else:
                console.print(f"[{COLOR_ERROR}][Error] No results to save![/]")

        elif choice == "5":  # Show Response Time Chart
            if results:
                reporter.generate_response_time_chart(results)
            else:
                console.print(f"[{COLOR_ERROR}][Error] No results to visualize![/]")

        # Handle dynamic special checks
        elif choice in special_check_choices:
            check_name = menu_options[choice].replace("Check ", "")  # Get original check name
            check_info = SPECIAL_CHECKS[check_name]
            check_function = check_info["function"]
            check_prompts = check_info["prompts"]

            args = {}
            # Collect arguments for the special check function from user prompts
            for prompt_info in check_prompts:
                name = prompt_info["name"]
                text = prompt_info["text"]
                default = prompt_info.get("default")
                choices = prompt_info.get("choices")
                input_type = prompt_info.get("type", "str")  # Default to string

                if input_type == "int":
                    value = Prompt.ask(
                        f"[{COLOR_PRIMARY}]{text}[/]",
                        default=str(default) if default is not None else None,
                    )
                    if value and value.isdigit():
                        args[name] = int(value)
                    else:
                        console.print(
                            f"[{COLOR_ERROR}][Error] Invalid input for {text}. Must be an integer.[/]"
                        )
                        continue  # Skip this check if input is invalid
                elif input_type == "bool":
                    value = Prompt.ask(
                        f"[{COLOR_PRIMARY}]{text}[/]", choices=choices, default=default
                    )
                    args[name] = value.lower() == "yes"
                else:  # 'str' or other types
                    args[name] = Prompt.ask(
                        f"[{COLOR_PRIMARY}]{text}[/]", default=default, choices=choices
                    )

            # Add timeout to args if the special check function accepts it
            if "timeout" in check_function.__code__.co_varnames:
                args["timeout"] = timeout

            # Validate host and port if they are arguments for the special check
            if "host" in args and not utils.validate_host(args["host"]):
                console.print(f"[{COLOR_ERROR}][Error] Invalid host format![/]")
            elif "port" in args and (
                not isinstance(args["port"], int) or args["port"] <= 0
            ):
                console.print(
                    f"[{COLOR_ERROR}][Error] Invalid port format! Port must be a positive integer." 
                )
            else:
                # Execute the special check function with collected arguments
                color, message = check_function(**args)
                console.print(f"[{color}]{message}[/{color}]")
                results.append((color, message))

        elif choice.lower() == "help":  # Display help menu
            menu_display = ""
            for num, text in menu_options.items():
                menu_display += f"{num}. {text}\n"

            console.print(menu_display.strip())

        elif choice == str(len(menu_options)):  # Exit option (last dynamic option)
            console.print(
                f"[{COLOR_SECONDARY}]Thank you for using HostHunter by hansobored![/]"
            )
            break  # Exit the main menu loop

        Prompt.ask(f"[{COLOR_PRIMARY}]Press Enter to continue...[/]")


def main():
    """
    Entry point for the HostHunter application.

    Initializes the main menu and handles graceful program termination
    in case of a KeyboardInterrupt (Ctrl+C).
    """
    try:
        main_menu()
    except KeyboardInterrupt:
        logging.info("Program terminated by user")
        console.print(f"\n[{COLOR_ERROR}][Exit] Program terminated by user.[/]")


if __name__ == "__main__":
    # This block ensures that main() is called only when the script is executed directly,
    # not when it's imported as a module.
    main()
