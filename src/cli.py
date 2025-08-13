import os
import logging
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from rich.panel import Panel
from rich.text import Text

# Changed relative imports to absolute imports
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
    config = utils.load_config()  # Load configuration
    utils.setup_logging(config)  # Pass config to setup_logging
    if not utils.check_dependencies():
        console.print(
            f"[{COLOR_ERROR}][Exit] Please install missing dependencies and try again.[/]"
        )
        return
    results = []
    while True:
        console.clear()
        utils.print_banner()

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

        warning_text = f"[{COLOR_WARNING}]Unauthorized use of this tool for quota exploitation may violate laws or service policies. Use only with explicit permission.[/]"
        console.print(
            Panel(
                warning_text,
                title=Text("WARNING", style=COLOR_ERROR),
                title_align="left",
                border_style=PANEL_BORDER_COLOR,
            )
        )

        menu_options = {
            "1": "Check Single Host",
            "2": "Check Ping",
            "3": "Scan Hosts from File",
            "4": "Save Results",
            "5": "Show Response Time Chart",
        }

        # Dynamically add special checks to the menu
        special_check_start_num = len(menu_options) + 1
        special_check_choices = []
        for i, (name, check_info) in enumerate(SPECIAL_CHECKS.items()):
            option_num = str(special_check_start_num + i)
            menu_options[option_num] = f"Check {name}"
            special_check_choices.append(option_num)

        menu_options[str(len(menu_options) + 1)] = "Exit"  # Add Exit option dynamically

        console.print(f"[{COLOR_CYAN}]type help for more information[/]")
        console.print()

        choice = Prompt.ask(f"╭─HostHunter──[[{COLOR_ERROR}]Error[/{COLOR_ERROR}]]\n╰─#")

        # Handle timeout prompt for relevant choices
        if (
            choice in ["1", "2", "3"] + special_check_choices
        ):  # Include dynamic special check choices
            timeout = Prompt.ask(
                f"[{COLOR_PRIMARY}]Enter timeout second default:[/]",
                default=config["General"]["default_timeout"],
            )
            if not timeout.isdigit() or int(timeout) <= 0:
                console.print(
                    f"[{COLOR_ERROR}][Error] Timeout must be a positive integer![/]"
                )
                timeout = int(config["General"]["default_timeout"])
            else:
                timeout = int(timeout)

        if choice == "1":
            host = Prompt.ask(f"[{COLOR_PRIMARY}]Enter host (e.g., cdn.udemy.com)[/]")
            port = Prompt.ask(f"[{COLOR_PRIMARY}]Enter port default:[/]", default="443")
            if utils.validate_host(host) and port.isdigit() and int(port) > 0:
                with console.status(f"[{COLOR_PRIMARY}]Checking {host}...", spinner="dots"):
                    color, message = host_checker.check_host(host, int(port), timeout)
                console.print(f"[{color}]{message}[/{color}]")
                results.append((color, message))
            else:
                console.print(
                    f"[{COLOR_ERROR}][Error] Invalid host or port format! Port must be a positive integer.[/]"
                )

        elif choice == "2":
            host = Prompt.ask(
                f"[{COLOR_PRIMARY}]Enter host to ping (e.g., cdn.udemy.com)[/]"
            )
            if utils.validate_host(host):
                with console.status(f"[{COLOR_PRIMARY}]Pinging {host}...", spinner="dots"):
                    color, message = host_checker.check_ping(host, timeout)
                console.print(f"[{color}]{message}[/{color}]")
                results.append((color, message))
            else:
                console.print(f"[{COLOR_ERROR}][Error] Invalid host format![/]")

        elif choice == "3":
            file_name = Prompt.ask(
                f"[{COLOR_PRIMARY}]Enter host file name in hosts folder (e.g., hosts.txt)[/]"
            )
            file_path = os.path.join(config["Paths"]["hosts_dir"], file_name)
            file_path = os.path.abspath(file_path)
            if os.path.exists(file_path):
                max_workers = int(config["General"]["max_concurrent_checks"])
                with console.status(f"[{COLOR_PRIMARY}]Scanning hosts from {file_name}...", spinner="dots"):
                    results.extend(scan_hosts_from_file(file_path, timeout, max_workers))
                if results:
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

        elif choice == "4":
            if results:
                output_format = Prompt.ask(
                    f"[{COLOR_PRIMARY}]Select output format[/]",
                    choices=["txt", "json", "csv"],
                    default="txt",
                )
                save_results(results, config["Paths"]["results_dir"], output_format)
            else:
                console.print(f"[{COLOR_ERROR}][Error] No results to save![/]")

        elif choice == "5":
            if results:
                reporter.generate_response_time_chart(results)
            else:
                console.print(f"[{COLOR_ERROR}][Error] No results to visualize![/]")

        # Handle dynamic special checks
        elif choice in special_check_choices:
            check_name = menu_options[choice].replace("Check ", "")  # Get original name
            check_info = SPECIAL_CHECKS[check_name]
            check_function = check_info["function"]
            check_prompts = check_info["prompts"]

            args = {}
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
                else:  # 'str' or other
                    args[name] = Prompt.ask(
                        f"[{COLOR_PRIMARY}]{text}[/]", default=default, choices=choices
                    )

            # Add timeout to args if it's a parameter for the function
            if "timeout" in check_function.__code__.co_varnames:
                args["timeout"] = timeout

            # Validate host if 'host' is an argument
            if "host" in args and not utils.validate_host(args["host"]):
                console.print(f"[{COLOR_ERROR}][Error] Invalid host format![/]")
            elif "port" in args and (
                not isinstance(args["port"], int) or args["port"] <= 0
            ):
                console.print(
                    "{COLOR_ERROR}[Error] Invalid port format! Port must be a positive integer."
                )
            else:
                color, message = check_function(**args)
                console.print(f"[{color}]{message}[/{color}]")
                results.append((color, message))

        elif choice.lower() == "help":
            menu_display = ""
            for num, text in menu_options.items():
                menu_display += f"{num}. {text}\n"

            console.print(menu_display.strip())

        elif choice == str(len(menu_options)):  # Exit option
            console.print(
                f"[{COLOR_SECONDARY}]Thank you for using HostHunter by hansobored![/]"
            )
            break

        Prompt.ask(f"[{COLOR_PRIMARY}]Press Enter to continue...[/]")


def main():
    try:
        main_menu()
    except KeyboardInterrupt:
        logging.info("Program terminated by user")
        console.print(f"\n[{COLOR_ERROR}][Exit] Program terminated by user.[/]")


if __name__ == "__main__":
    main()
