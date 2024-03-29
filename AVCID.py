import os
import re
import clipboard
import requests
import PySimpleGUI as sg
from urllib.parse import urlparse
from io import StringIO
import matplotlib.font_manager 

def main():  
    
    # Define the layout for the settings window
    settings_layout = [
        [sg.Text('Font Size'), sg.Input(default_text='12', key='-FONT_SIZE-', size=(5, 1))],
        [sg.Text('Theme'), sg.Combo(sg.theme_list(), default_value=sg.theme(), key='-THEME-')],
        [sg.Text('Font Style'), sg.Combo([f.name for f in matplotlib.font_manager.fontManager.ttflist], default_value='Verdana', key='-FONT_STYLE-')],
        [sg.Button('Apply'), sg.Button('Cancel')]
    ]


    site_search_files = [r'\\MYWEB02.verizon.com\TestTeam$\Production\TestTeam\phonebook\DB_G-sort.csv']
    appdata = os.path.expandvars(r"%APPDATA%")
    default_phonebook_file = r"\\MYWEB02.verizon.com\TestTeam$\Production\TestTeam\phonebook\contacts.txt"
    last_phonebook_file = os.path.join(appdata, r"NMC_AIO\phonebook.csv")
    last_site_search_file= os.path.join(appdata, r"NMC_AIO\sitesearch.csv")
    log_file = os.path.join(appdata, r"Avaya\one-X Agent\2.5\Log Files\OneXAgent.log")

    # Try to load the last used phonebook and site search file
    try:
        with open(last_phonebook_file, 'r', encoding='utf-8', errors='ignore') as file:
            phonebook_file = file.read().strip() or default_phonebook_file
    except FileNotFoundError:
        phonebook_file = default_phonebook_file

    # If the phonebook file does not exist, ask the user to provide it
    if not os.path.exists(phonebook_file):
        sg.popup('The phonebook file does not exist. Please select a new file.')
        phonebook_file = sg.popup_get_file('Select a new phonebook file', no_window=True)
        if phonebook_file is None:
            sg.popup('No phonebook file selected. The program will now exit.')
            return

    try:
        with open(last_site_search_file, 'r', encoding='utf-8', errors='ignore') as file:
            site_search_files = file.read().strip().split(';')
            site_search_entries = []
            for file_name in site_search_files:
                site_search_entries.extend(read_phonebook(file_name))
    except FileNotFoundError:
        site_search_entries = []

    phonebook_entries = read_phonebook(phonebook_file)
    site_search_entries = []
    for file_name in site_search_files:
        site_search_entries.extend(read_phonebook(file_name))

    current_caller_phone, caller_match = update_current_caller(log_file, phonebook_file)


    current_call_tab_layout = [
        [sg.Text("Current Caller:", font=('Arial', 10, 'bold')), sg.Text(current_caller_phone, key='-CURRENT_CALLER_PHONE-', size=(15, None), font=('Arial', 10, 'bold')), sg.Button("Copy to clipboard", key='-COPY_TO_CLIPBOARD-', pad=((5, 0), 0), font=('Arial', 10, 'bold'))],
        [sg.Text(caller_match, key='-CALLER_MATCH-', font=('Arial', 10, 'bold'))]
    ]
    phonebook_tab_layout = [
        [sg.Input(key='-SEARCH_QUERY-', enable_events=True, default_text='Search Here', size=(40, 1), expand_x=True), sg.Button("Copy Match", key='-COPY_MATCH_BUTTON-')],
        [sg.Listbox(phonebook_entries, key='-SEARCH_RESULTS-', size=(73, 10), enable_events=True, expand_x=True, expand_y=True)],  
        [sg.Text(f'Matches: 0 | Total Entries: {len(phonebook_entries)}', size=(65, 1), key='-SEARCH_STATS-')]
    ]

    site_search_tab_layout = [
        [sg.Input(key='-SITE_SEARCH_QUERY-', enable_events=True, default_text='Search Here', size=(40, 1), expand_x=True), sg.Button("Copy Match", key='-COPY_SITE_MATCH_BUTTON-')],
        [sg.Listbox(site_search_entries, key='-SITE_SEARCH_RESULTS-', size=(73, 10), enable_events=True, expand_x=True, expand_y=True)],  
        [sg.Text(f'Matches: 0 | Total Entries: {len(site_search_entries)}', size=(65, 1), key='-SITE_SEARCH_STATS-')]
    ]

 
    layout = [
        [sg.Menu([['File', ['ChangePhonebook', 'ChangeSiteSearch']], ['Settings', ['Change Font Size, Style and Theme']]])],
        [sg.TabGroup([[sg.Tab('Current Call', current_call_tab_layout, expand_x=True, expand_y=True), sg.Tab('Phonebook', phonebook_tab_layout, expand_x=True, expand_y=True), sg.Tab('Site Search', site_search_tab_layout, expand_x=True, expand_y=True)]], expand_x=True, expand_y=True)]
    ]
    window = sg.Window("Avaya Caller ID", layout, resizable=True, finalize=True)

    while True:
        event, values = window.read(timeout=1000)  # 5 seconds

        if event == sg.WINDOW_CLOSED:
            break
        
        elif event == 'Change Font Size, Style and Theme':
            settings_window = sg.Window('Settings', settings_layout)
            while True:
                settings_event, settings_values = settings_window.read()
                if settings_event in (sg.WINDOW_CLOSED, 'Cancel'):
                    break
                elif settings_event == 'Apply':
                    font_size = int(settings_values['-FONT_SIZE-'])
                    theme = settings_values['-THEME-']
                    font_style = settings_values['-FONT_STYLE-']
                    sg.set_options(font=(font_style, font_size))
                    sg.theme(theme)
                    settings_window.close()
            settings_window.close()

        elif event == 'Change Font Size and Theme':
            settings_window = sg.Window('Settings', settings_layout)
            while True:
                settings_event, settings_values = settings_window.read()
                if settings_event in (sg.WINDOW_CLOSED, 'Cancel'):
                    break
                elif settings_event == 'Apply':
                    font_size = int(settings_values['-FONT_SIZE-'])
                    theme = settings_values['-THEME-']
                    sg.set_options(font=('Helvetica', font_size))
                    sg.theme(theme)
                    settings_window.close()
            settings_window.close()
        elif event == '-COPY_TO_CLIPBOARD-':
            clipboard.copy(caller_match)

        elif event == '-COPY_MATCH_BUTTON-':
            if values['-SEARCH_RESULTS-']:  # Add check if list is not empty
                match = values['-SEARCH_RESULTS-'][0]  # Assuming first element in listbox is selected
                clipboard.copy(match)
    
        # Handle copy match event from the site search
        elif event == '-COPY_SITE_MATCH_BUTTON-':
            if values['-SITE_SEARCH_RESULTS-']:  # Check if list is not empty
                match = values['-SITE_SEARCH_RESULTS-'][0]  # Assuming first element in listbox is selected
                clipboard.copy(match)
                
        elif event == 'ChangePhonebook':
            filename = sg.popup_get_file('Change Phonebook CSV', no_window=True, file_types=(("Text Files", "*.*"),), multiple_files=False)
            if filename:
                phonebook_file = filename
                phonebook_entries = read_phonebook(phonebook_file)
                window['-SEARCH_RESULTS-'].update(values=phonebook_entries)  
                window['-SEARCH_STATS-'].update(f'Matches: 0 | Total Entries: {len(phonebook_entries)}')
                with open(last_phonebook_file, 'w', encoding='utf-8', errors='ignore') as file:
                    file.write(phonebook_file)
        elif event == 'ChangeSiteSearch':
            filenames = sg.popup_get_file('Change Site Search File', no_window=True, file_types=(("Text Files", "*.*"),), multiple_files=True)
            if filenames:
                if isinstance(filenames, tuple):
                    site_search_files = list(filenames)
                else:
                    site_search_files = filenames.split(';')
                site_search_entries = []
                for file in site_search_files:
                    site_search_entries.extend(read_phonebook(file))
                window['-SITE_SEARCH_RESULTS-'].update(values=site_search_entries)  
                window['-SITE_SEARCH_STATS-'].update(f'Matches: 0 | Total Entries: {len(site_search_entries)}')
                with open(last_site_search_file, 'w', encoding='utf-8', errors='ignore') as file:
                    file.write(';'.join(site_search_files))


        elif event == '-SEARCH_QUERY-':  
            search_query = values['-SEARCH_QUERY-'].lower()
            if search_query == '':
                filtered_entries = [phonebook_entries[0]] if phonebook_entries else []
            else:
                filtered_entries = search_phonebook(phonebook_entries, search_query)
            window['-SEARCH_RESULTS-'].update(values=filtered_entries)  
            window['-SEARCH_RESULTS-'].set_focus()  # Set focus to the listbox
            window['-SEARCH_RESULTS-'].update(set_to_index=0)  # Select the first item
            window['-SEARCH_STATS-'].update(f'Matches: {len(filtered_entries)} |  Total Entries: {len(phonebook_entries)}')
        
        elif event == '-SITE_SEARCH_QUERY-':  
            search_query = values['-SITE_SEARCH_QUERY-'].lower()
            if search_query == '':
                # if search_query is empty, select the first entry in the site_search_entries
                filtered_entries = [site_search_entries[0]] if site_search_entries else []
            else:
                filtered_entries = search_phonebook(site_search_entries, search_query)
            window['-SITE_SEARCH_RESULTS-'].update(values=filtered_entries)  
            window['-SITE_SEARCH_STATS-'].update(f'Matches: {len(filtered_entries)} | Total Entries: {len(site_search_entries)}')

        current_caller_phone, caller_match = update_current_caller(log_file, phonebook_file)
        window['-CURRENT_CALLER_PHONE-'].update(current_caller_phone)
        window['-CALLER_MATCH-'].update(caller_match)

    window.close()


def update_current_caller(log_file, phonebook_file):
    with open(log_file, 'r', encoding='cp1252') as log_file:
        log_lines = log_file.readlines()

    phone_number = None
    for line in log_lines[::-1]:
        match = re.search(r'RemoteParty=\[(\d{3}-\d{3}-\d{4}),\d{10}\]', line)
        if match:
            phone_number = match.group(1)
            break

    if phone_number:
        caller_match = match_caller_to_phonebook(phone_number, phonebook_file)
    else:
        caller_match = "No phone number found"

    return phone_number, caller_match


def match_caller_to_phonebook(phone_number, phonebook_file):
    with open(phonebook_file, 'r', encoding='utf-8', errors='ignore') as file:
        lines = file.readlines()

    matches = []  # to store matching lines

    for line in lines:
        line = ' '.join(line.split('\t'))
        if phone_number in line:
            entry = line.strip().split(' ')
            formatted_entry = ' '.join(entry)
            matches.append(formatted_entry)

    if matches:
        return "\n".join(matches)
    else:
        return f"No match found for {phone_number}"

def read_phonebook(phonebook_file):
    with open(phonebook_file, 'r', encoding='utf-8', errors='ignore') as file:
        lines = file.readlines()
    return [line.replace('\t', ' ') for line in lines]

def search_phonebook(lines, search_query):
    results = []
    for line in lines:
        if search_query in line.lower():
            entry = line.strip().split(',')
            formatted_entry = ' - '.join(entry)
            results.append(formatted_entry)

    return results


if __name__ == '__main__':
    main()
