#import h5py
import numpy as np
from rdkit import Chem

def convert_to_smiles(vector, char):
    list_char = list(char)
    #list_char = char.tolist()
    vector = vector.astype(int)
    return "".join(map(lambda x: list_char[x], vector)).strip()

def stochastic_convert_to_smiles(vector, char):
    list_char = char.tolist()
    s = ""
    for i in range(len(vector)):
        prob = vector[i].tolist()
        norm0 = sum(prob)
        prob = [i/norm0 for i in prob]
        index = np.random.choice(len(list_char), 1, p=prob)
        s+=list_char[index[0]]
    return s

def one_hot_array(i, n):
    return list(map(int, [ix == i for ix in range(n)]))

def one_hot_index(vec, charset):
    return list(map(charset.index, vec))

def from_one_hot_array(vec):
    oh = np.where(vec == 1)
    return None if oh[0].shape == (0, ) else int(oh[0][0])

def decode_smiles_from_indexes(vec, charset):
    return "".join(map(lambda x: charset[x], vec)).strip()

def load_dataset(filename, split = True):
    h5f = h5py.File(filename, 'r')
    data_train = h5f['data_train'][:] if split else None
    data_test = h5f['data_test'][:]
    charset = h5f['charset'][:]
    h5f.close()
    return (data_train, data_test, charset) if split else (data_test, charset)

def encode_smiles(smiles, model, charset):
    cropped = list(smiles.ljust(120))
    preprocessed = np.array([list(map(lambda x: one_hot_array(x, len(charset)), one_hot_index(cropped, charset)))])
    return model.encoder.predict(preprocessed)

def smiles_to_onehot(smiles, charset):
    cropped = list(smiles.ljust(120))
    return np.array(
        [
            list(
                map(
                    lambda x: one_hot_array(x, len(charset)),
                    one_hot_index(cropped, charset),
                )
            )
        ]
    )

def smiles_to_vector(smiles, vocab, max_length):
    while len(smiles)<max_length:
        smiles +=" "
    return [vocab.index(str(x)) for x in smiles]

def decode_latent_molecule(latent, model, charset, latent_dim):
    decoded = model.decoder.predict(latent.reshape(1, latent_dim)).argmax(axis=2)[0]
    return decode_smiles_from_indexes(decoded, charset)

def interpolate(source_smiles, dest_smiles, steps, charset, model, latent_dim):
    source_latent = encode_smiles(source_smiles, model, charset)
    dest_latent = encode_smiles(dest_smiles, model, charset)
    step = (dest_latent - source_latent) / float(steps)
    results = []
    for i in range(steps):
        item = source_latent + (step * i)        
        decoded = decode_latent_molecule(item, model, charset, latent_dim)
        results.append(decoded)
    return results

def get_unique_mols(mol_list):
    inchi_keys = [Chem.InchiToInchiKey(Chem.MolToInchi(m)) for m in mol_list]
    u, indices = np.unique(inchi_keys, return_index=True)
    return [[mol_list[i], inchi_keys[i]] for i in indices]

def accuracy(arr1, arr2, length):
    total = len(arr1)
    count2=0
    count3=0
    count1 = sum(
        1
        for i in range(len(arr1))
        if np.array_equal(arr1[i, : length[i]], arr2[i, : length[i]])
    )
    for i in range(len(arr1)):
        for j in range(length[i]):
            if arr1[i][j]==arr2[i][j]:
                count2+=1
            count3+=1

    return float(count1/float(total)), float(count2/count3)
def extract_vocab(filename, seq_length):
    import collections
    with open(filename) as f:
        lines = f.read().split('\n')[:-1]
    lines = [l.split() for l in lines]
    lines = [l for l in lines if len(l[0])<seq_length-2]
    smiles = [l[0] for l in lines]

    total_string = ''.join(smiles)
    counter = collections.Counter(total_string)
    count_pairs = sorted(counter.items(), key=lambda x: -x[1])
    chars, counts = zip(*count_pairs)
    vocab = dict(zip(chars, range(len(chars))))

    chars+=('E',) #End of smiles
    chars+=('X',) #Start of smiles
    vocab['E'] = len(chars)-2
    vocab['X'] = len(chars)-1
    return chars, vocab

def load_data(filename, seq_length, char, vocab):
    with open(filename) as f:
        lines = f.read().split('\n')[:-1]
    smiles = [l for l in lines if len(l)<seq_length-2]
    smiles_input = []
    smiles_output = []
    length = []
    for s in smiles:
        length.append(len(s)+1)
        s1 = f'X{s}'.ljust(seq_length, 'E')
        s2 = s.ljust(seq_length, 'E')
        list1 = list(map(vocab.get, s1))
        list2 = list(map(vocab.get, s2))
        if None in list1 or None in list2: continue
        smiles_input.append(list1)
        smiles_output.append(list2)
    smiles_input = np.array(smiles_input)
    smiles_output = np.array(smiles_output)
    length = np.array(length)

    return smiles_input, smiles_output, length 

