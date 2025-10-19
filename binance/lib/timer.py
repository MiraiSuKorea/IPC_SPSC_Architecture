import time
from datetime import datetime
import sys
import pandas as pd
import os
def print_initial_box(title, max_width=150):
    """
    Print the static box structure.

    :param max_width: Maximum width of the box.
    """
    # Calculate padding for the title to center it
    padding_left = int((max_width - 2 - len(title)) / 2)
    padding_right = max_width - 2 - len(title) - padding_left

    # Print the top border of the box
    print('┌' + '─' * (max_width - 2) + '┐')

    # Print the title line centered
    print('│' + ' ' * padding_left + title + ' ' * padding_right + '│')


    # Print the bottom border of the box
    print('└' + '─' * (max_width - 2) + '┘')

    # Move cursor up one line for upcoming message updates
    print('\033[A', end='')

def timer_in_box(msg, max_width=150):
    """
    Update the message inside the static box.

    :param msg: Message to be updated inside the box.
    :param max_width: Maximum width of the box.
    """
    # Truncate message if it's longer than the box width
    if len(msg) > max_width - 4:
        msg = msg[:max_width - 7] + '...'

    # Center the message inside the box
    padded_message = msg.center(max_width - 4)

    # Overwrite the message line inside the box
    print(f'\r│{padded_message}│', end='')


def print_static_box(max_width=150):
    """Print the static parts of the box, excluding the dynamic message line."""
    print('┌' + '─' * (max_width - 2) + '┐')  # Top border
    # Add a placeholder space for the dynamic message content; will not be used directly.
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')

    print('└' + '─' * (max_width - 2) + '┘')  # Bottom border
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('└' + '─' * (max_width - 2) + '┘')  # Bottom border
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('└' + '─' * (max_width - 2) + '┘')  # Bottom border


def print_trading_static_box(max_width=150):
    """Print the static parts of the box, excluding the dynamic message line."""
    print('┌' + '─' * (max_width - 2) + '┐')  # Top border
    # Add a placeholder space for the dynamic message content; will not be used directly.
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('│' + ' ' * (max_width - 2) + '│')
    print('└' + '─' * (max_width - 2) + '┘')  # Bottom border

def update_logs_in_box(log_file_path, max_width=150, line_count=20):
    # Read the last few lines from the log file.
    abspath = os.path.abspath(__file__)
    dname = os.path.dirname(abspath)
    os.chdir(dname)
    with open(log_file_path, 'r') as file:
        lines = file.readlines()[-line_count:]

    # Move cursor to the beginning of the last box.
        # Move cursor up to the bottom message line inside the box, update it
    sys.stdout.write(f'\033[42A')  # Adjust the number based on box size
    sys.stdout.write(f'\033[20B')  # Move up to the bottom content line
    for line in lines:
        formatted_line = line.strip().ljust(max_width - 2)
        sys.stdout.write(f'\r│{formatted_line}│\n')
    sys.stdout.flush()
def update_message_in_box(msg, percentage, max_width=150, log_check=True, log_file='status_log.txt'):
    """
    Update a single message inside the box at the top left without redrawing the entire box or adding new lines.
    Log the message to a file.

    :param msg: The message to display.
    :param percentage: The current progress percentage.
    :param max_width: The maximum width of the box.
    :param log_file: The file path for logging messages.
    """

    abspath = os.path.abspath(__file__)
    dname = os.path.dirname(abspath)
    os.chdir(dname)


    current_utc_time = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

    # Define and create the progress bar.
    progress_width = int(max_width * 0.3)
    filled_length = int(progress_width * percentage // 100)
    bar = '[' + '█' * filled_length + '-' * (progress_width - filled_length) + ']'

    # Compose and trim the message to fit in the available space.
    available_space = max_width - len(current_utc_time) - len(bar) - 7
    trimmed_msg = (msg[:available_space - 3] + '...') if len(msg) > available_space else msg
    full_msg = f"{current_utc_time} {bar} {trimmed_msg}".ljust(max_width - 2)


    # Move cursor up to the message line and update it.
    sys.stdout.write(f'\033[42A')  # Adjust the number based on box size
    sys.stdout.write('\033[1B')
    sys.stdout.write(f'\r│{full_msg}│\n')  # Overwrite content line.
    #sys.stdout.write(f'\033[1A')  # Move cursor up to position after box's bottom border.
    sys.stdout.flush()

    # Log the message.
    if log_check == True:
        try:
            with open(log_file, 'a') as file:
                file.write(f"{current_utc_time} - {msg}\n")
        except Exception as e:
            print(f"Error writing to log file: {e}")

    update_logs_in_box(log_file,150,20)


def countdown_timer(total_seconds, max_width=150, log_file='status_log.txt'):
    """
    Perform a countdown within the same static box on the console.

    :param total_seconds: Total seconds for the countdown.
    :param max_width: Maximum width of the box.
    """
    for i in range(total_seconds, -1, -1):
        msg = f"Time left: {i} seconds. To force quit, press ctrl + c."
        percentage = int(100 * (total_seconds - i) / total_seconds)
        update_message_in_box(msg, percentage, max_width, False, log_file)
        time.sleep(1)

def countdown_timer_order(total_seconds,orders, max_width=150, log_file='status_log.txt'):
    """
    Perform a countdown within the same static box on the console.

    :param total_seconds: Total seconds for the countdown.
    :param max_width: Maximum width of the box.
    """
    for i in range(total_seconds, -1, -1):
        msg = f"Time left: {i} seconds. {orders} orders stacked"
        percentage = int(100 * (total_seconds - i) / total_seconds)
        update_message_in_box(msg, percentage, max_width, False, log_file)
        time.sleep(1)

def update_bottom_message_in_box(msg, max_width=150, log_file='status_log.txt'):
    """
    Update the message at the bottom inside the box without redrawing the entire box.
    Log the message to a file.
    """
    # Move cursor up to the bottom message line inside the box, update it
    sys.stdout.write(f'\033[42A')  # Adjust the number based on box size
    sys.stdout.write(f'\033[4B')  # Move up to the bottom content line
    available_space = max_width - 40
    trimmed_msg = (msg[:available_space - 3] + '...') if len(msg) > available_space else msg
    full_msg = f" {msg}".ljust(max_width - 2)

    sys.stdout.write(f'\r│{trimmed_msg}│')
    sys.stdout.flush()
    abspath = os.path.abspath(__file__)
    dname = os.path.dirname(abspath)
    os.chdir(dname)
    # Log the message
    with open(log_file, 'a') as file:
        file.write(f"{datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')} - {msg}\n")



def update_2bottom_message_in_box(msg, max_width=150, log_file='status_log.txt'):
    """
    Update the message at the bottom inside the box without redrawing the entire box.
    Log the message to a file.
    """
    # Move cursor up to the bottom message line inside the box, update it
    sys.stdout.write(f'\033[42A')  # Adjust the number based on box size
    sys.stdout.write(f'\033[17B')  # Move up to the bottom content line
    available_space = max_width - 40
    trimmed_msg = (msg[:available_space - 3] + '...') if len(msg) > available_space else msg
    full_msg = f" {msg}".ljust(max_width - 2)
    sys.stdout.write(f'\r│{trimmed_msg}│')
    sys.stdout.flush()

    # Log the message
    with open(log_file, 'a') as file:
        file.write(f"{datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')} - {msg}\n")

def update_dataframe_in_box(df, max_width=150, line_count=15):
    # Read the dataframe from an external file.
    # Convert the last few rows of the dataframe to a string, limiting the output.
    df_str = df.tail(line_count).to_string(index=False, header=True)

    # Split the dataframe string into lines for display.
    lines = df_str.split('\n')

    # Move cursor to the beginning of the second box.
    sys.stdout.write(f'\033[42A')  # Adjust the number based on box size
    sys.stdout.write(f'\033[4B')  # Move up to the bottom content line

    for line in lines:
        formatted_line = line.ljust(max_width - 4)
        sys.stdout.write(f'\r│{formatted_line}│\n')
    sys.stdout.flush()

def update_balance_dataframe_in_box(df, max_width=150, line_count=15):
    # Read the dataframe from an external file.
    # Convert the last few rows of the dataframe to a string, limiting the output.
    df_str = df.tail(line_count).to_string(index=False, header=True)

    # Split the dataframe string into lines for display.
    lines = df_str.split('\n')

    # Move cursor to the beginning of the second box.
    sys.stdout.write(f'\033[42A')  # Adjust the number based on box size
    sys.stdout.write(f'\033[4B')  # Move up to the bottom content line

    for line in lines:
        formatted_line = line.ljust(max_width - 4)
        sys.stdout.write(f'\r│{formatted_line}│\n')
    sys.stdout.flush()
def update_order_dataframe_in_box(df, max_width=150, line_count=15):
    # Read the dataframe from an external file.
    # Convert the last few rows of the dataframe to a string, limiting the output.
    df = df.drop(columns=['orderId', 'orderListId', 'clientOrderId', 'transactTime',
                                                 'cummulativeQuoteQty', 'timeInForce', 'workingTime',
                                                 'selfTradePreventionMode'])

    df_str = df.tail(line_count).to_string(index=False, header=True)

    # Split the dataframe string into lines for display.
    lines = df_str.split('\n')

    # Move cursor to the beginning of the second box.
    sys.stdout.write(f'\033[42A')  # Adjust the number based on box size
    sys.stdout.write(f'\033[16B')  # Move up to the bottom content line
    for line in lines:
        formatted_line = line.ljust(max_width - 4)
        sys.stdout.write(f'\r│{formatted_line}│\n')
    sys.stdout.flush()

def update_execution_dataframe_in_box(df, max_width=150, line_count=15):
    # Read the dataframe from an external file.
    # Convert the last few rows of the dataframe to a string, limiting the output.
    df = df.drop(columns=['E','c','o','f','P','F','g','C','X','r','i','l','z','L','n','N','T','t','I','w','m','M','O','Z','Y','Q','W','V'])
    df_str = df.tail(line_count).to_string(index=False, header=True)

    # Split the dataframe string into lines for display.
    lines = df_str.split('\n')

    # Move cursor to the beginning of the second box.
    sys.stdout.write(f'\033[42A')  # Adjust the number based on box size
    sys.stdout.write(f'\033[20B')  # Move up to the bottom content line

    for line in lines:
        formatted_line = line.ljust(max_width - 4)
        sys.stdout.write(f'\r│{formatted_line}│\n')
    sys.stdout.flush()



def update_dataframe_middle_in_box(df, max_width=150, line_count=15):
    # Read the dataframe from an external file.
    # Convert the last few rows of the dataframe to a string, limiting the output.
    df_str = df.tail(line_count).to_string(index=False, header=True)

    # Split the dataframe string into lines for display.
    lines = df_str.split('\n')

    # Move cursor to the beginning of the second box.
    sys.stdout.write(f'\033[42A')  # Adjust the number based on box size
    sys.stdout.write(f'\033[4B')  # Move up to the bottom content line


    for line in lines:
        formatted_line = line.ljust(max_width - 54)
        sys.stdout.write(f'\r \033[50C │{formatted_line}│\n')
    sys.stdout.flush()


def update_dataframe_right_in_box(df, max_width=150, line_count=20):
    # Read the dataframe from an external file.
    # Convert the last few rows of the dataframe to a string, limiting the output.
    df_str = df.tail(line_count).to_string(index=False, header=True)

    # Split the dataframe string into lines for display.
    lines = df_str.split('\n')

    # Move cursor to the beginning of the second box.
    sys.stdout.write(f'\033[42A')  # Adjust the number based on box size
    sys.stdout.write(f'\033[4B')  # Move up to the bottom content line


    for line in lines:
        formatted_line = line.ljust(max_width - 89)
        sys.stdout.write(f'\r \033[85C │{formatted_line}│\n')
    sys.stdout.flush()
