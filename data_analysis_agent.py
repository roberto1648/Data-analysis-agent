import numpy as np
import pandas as pd
import copy
from smolagents import OpenAIServerModel
from smolagents import CodeAgent
from smolagents import tool
import json
import os


def run(
    query="What was the average scheduled quantity in 2022?",
    data_filepath='pipeline_data.parket',
    processed_data_dirpath='data',
    api_key='',
):
    model = get_model(api_key)

    if not is_preprocessed_already(processed_data_dirpath):
        data_df = load_and_process_data(data_filepath)
        data_df, itoses, stois = numericalize_string_columns(data_df)
        save_preprocessed_objects(
            processed_data_dirpath, data_df, itoses, stois,
        )

    run_agent(query, model, processed_data_dirpath)


def run_agent(
    query = "What was the average scheduled quantity in 2022?",
    model=None,
    processed_data_dirpath='data',
):
    additional_args = {
        'data_df_path': os.path.join(processed_data_dirpath, 'data_df.csv'),
        'pipeline_name_itos_path': os.path.join(processed_data_dirpath, 'pipeline_name_itos.json'),
        'loc_name_itos_path': os.path.join(processed_data_dirpath, 'loc_name_itos.json'),
        'connecting_entity_itos_path': os.path.join(processed_data_dirpath, 'connecting_entity_itos.json'),
        'category_short_itos_path': os.path.join(processed_data_dirpath, 'category_short_itos.json'),
        'state_abb_itos_path': os.path.join(processed_data_dirpath, 'state_abb_itos.json'),
        'county_name_itos_path': os.path.join(processed_data_dirpath, 'county_name_itos.json'),
        'pipeline_name_stoi_path': os.path.join(processed_data_dirpath, 'pipeline_name_stoi.json'),
        'loc_name_stoi_path': os.path.join(processed_data_dirpath, 'loc_name_stoi.json'),
        'connecting_entity_stoi_path': os.path.join(processed_data_dirpath, 'connecting_entity_stoi.json'),
        'category_short_stoi_path': os.path.join(processed_data_dirpath, 'category_short_stoi.json'),
        'state_abb_stoi_path': os.path.join(processed_data_dirpath, 'state_abb_stoi.json'),
        'county_name_stoi_path': os.path.join(processed_data_dirpath, 'county_name_stoi.json'),
    }
    print(additional_args, '\n\n')

    additional_authorized_imports = [
        'numpy.*', 'pandas.*', 'sklearn.*', 'matplotlib.*', 'seaborn.*', 'json.*',
        'os.*',  # added since it keeps looking for it
        'pathlib.*',  # it was also trying to get this
    ]

    task = (
        'Open the pandas dataframe saved at "data_df_path" '
        f'and answer the following query: {query}.\n\n'

        'To help you in your task the values in some columns have been '
        'already transformed into numerical values. The transformed columns are:\n\n'
        '"pipeline_name", "loc_name", "connecting_entity", "category_short", "state_abb", "county_name".\n\n'
        'The integer to string transformation for each column are provided to you as dictionaries '
        'saved in json files denoted as "[column_name]_itos_path". '
        'The inverse (string to integer) transformations are also provided as dictionaries '
        'saved at json files denoted as "[column_name]_stoi_path". '
        'You must use the provided "open_json" function to open the stoi or itos files above. '
        'Please refer to these transformations if there is any user mention to a specific column category name. '
        'Also, where applicable, refer to any column category by name in your final answer.\n\n'

        'Provide your answer as a detailed report in which insights and any caveats are discussed. '
        'The report must be clearly readable by a human. Any names must be specified '
        '(e.g., avoid referring to any object as "UNK"). '
        'If suitable, include visualizations. '
        'There is also limited time for processing. Code in each iteration should take less than ~10 min to run.\n\n'
    )
    print(task, '\n\n')

    agent = CodeAgent(
        tools=[open_json],
        model=model if model is not None else get_model(),
        add_base_tools=True,
        additional_authorized_imports=additional_authorized_imports,
        planning_interval=1,
    )

    agent.run(
        task=task,
        additional_args=additional_args,
    )


def get_model(api_key=''):
    if api_key == '': api_key = input('Please enter your openai api key')
    model = OpenAIServerModel(
        model_id="gpt-5",
        api_key=api_key,
    )

    return model


def load_and_process_data(
        filepath='pipeline_data.parquet',
):
    df = pd.read_parquet(filepath)
    df = df.fillna(np.nan)
    q = df['scheduled_quantity']
    d = pd.to_datetime(df['eff_gas_day'])
    df = df[
        [
            'pipeline_name', 'loc_name',
            # 'connecting_pipeline',
            'connecting_entity',
            'rec_del_sign', 'category_short',
            # 'country_name',
            'state_abb',
            'county_name',
            # 'latitude', 'longitude',
            # 'eff_gas_day',
            # 'scheduled_quantity'
        ]
    ].copy()
    df['year'] = d.dt.year
    df['month'] = d.dt.month
    df['day_of_month'] = d.dt.day
    df['scheduled_quantity'] = q
    df = df.dropna()

    return df


def numericalize(ser):
    vals = ser.unique()
    vals = pd.Series(vals).sort_values().values
    itos = {k: str(s) for k, s in enumerate(vals)}
    stoi = {str(s): k for k, s in enumerate(vals)}
    num_ser = ser.apply(lambda s: stoi[s])

    return num_ser, itos, stoi


def numericalize_string_columns(df_in):
    df_out = df_in.copy()
    cols = [
        'pipeline_name', 'loc_name', 'connecting_entity',
        'category_short', 'state_abb', 'county_name'
    ]
    stois, itoses = {}, {}

    for col in cols:
        num_ser, itos, stoi = numericalize(df_in[col])
        df_out[col] = num_ser.copy()
        stois[col] = copy.deepcopy(stoi)
        itoses[col] = copy.deepcopy(itos)

    return df_out, itoses, stois


def save_json(filepath, o):
    with open(filepath, 'w') as fp:
        fp.write(json.dumps(o, indent=4))


def save_preprocessed_objects(dirpath, data_df, itoses, stois):
    os.makedirs(dirpath, exist_ok=True)
    data_df.to_csv(os.path.join(dirpath, 'data_df.csv'), index=False)
    cols = ['pipeline_name', 'loc_name', 'connecting_entity', 'category_short', 'state_abb', 'county_name']

    for col in cols:
        save_json(os.path.join(dirpath, f'{col}_itos.json'), itoses[col])
        save_json(os.path.join(dirpath, f'{col}_stoi.json'), stois[col])


def is_preprocessed_already(dirpath):
    a = os.path.exists(os.path.join(dirpath, 'data_df.csv'))
    cols = ['pipeline_name', 'loc_name', 'connecting_entity', 'category_short', 'state_abb', 'county_name']

    for col in cols:
        a &= os.path.exists(os.path.join(dirpath, f'{col}_itos.json'))
        a &= os.path.exists(os.path.join(dirpath, f'{col}_stoi.json'))

    return a


@tool
def open_json(file_path: str) -> dict:
    """Reads a dictionary from a json file.

    Args:
        file_path: The path to the local json file to be read.
    """
    with open(file_path, 'r') as fp:
        return json.loads(fp.read())


if __name__ == '__main__':
    query = input('Please enter your query and press enter: ')
    data_filepath = input(
        'Please enter the data file path (default: pipeline_data.parquet), for default leave empty and press enter: '
    )
    processed_data_dirpath = input(
        'Please enter a path to a directory for saving processed data in (default: data), for default leave empty and press enter: '
    )
    api_key = input(
        'Please enter you openai api key: '
    )
    run(
        query=query,
        data_filepath=data_filepath if data_filepath else 'pipeline_data.parquet',
        processed_data_dirpath=processed_data_dirpath if processed_data_dirpath else 'data',
        api_key=api_key,
    )

