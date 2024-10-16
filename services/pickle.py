import pickle


def init_pickle_file(name):
    loaded_data = []
    with open(f"{name}.pickle", "wb") as file:
        pickle.dump(loaded_data, file)


def add_pickle(object, file_name="data.pickle"):
    # with open("data.pickle", "wb") as file:
    #     pickle.dump(object, file)
    loaded_data = []
    with open(file_name, "rb") as file:
        loaded_data = pickle.load(file)
        loaded_data.append(object)
    with open(file_name, "wb") as file:
        pickle.dump(loaded_data, file)


def update_pickle(user_id, key, value, file_name="data.pickle"):
    temp = []
    with open(file_name, "rb") as file:
        loaded_data = pickle.load(file)
        for data in loaded_data:
            if data.get('user_id') == user_id:
                index = loaded_data.index(data)
                data[key] = value
                loaded_data[index] = data
                temp = loaded_data

    with open(file_name, "wb") as file:
        pickle.dump(temp, file)


def get_pickle(user_id, file_name="data.pickle"):
    with open(file_name, "rb") as file:
        loaded_data = pickle.load(file)
        for data in loaded_data:
            if data.get('user_id') == user_id:
                return data
        return None


def check_user_exist(user_id):
    is_exist = False
    with open("data.pickle", "rb") as file:
        loaded_data = pickle.load(file)
        for data in loaded_data:
            if data.get('user_id') == user_id:
                is_exist = True
    return is_exist


def reset_pickle():
    with open("data.pickle", "wb") as file:
        pickle.dump([], file)
