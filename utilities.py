import numpy as np
import matplotlib.pyplot as plt
from pandas import read_csv
from preproc import *

config = {
    'data_folder': 'data/real_world_new/'
}

preproc_config = {
    'Fs': 6400,                 # Measured loads frequency
    #'Fs': 2*650+50,              # Generated loads frequency
    'sample_time': 0.1,
    'noise': False,
    'noise_percentage': 0,
    'train_test_ratio': 0.9,
    'threshold': 1
}

nn_config = {
    'input_size': 7,
    'output_size': 5,
    'num_classes': 5,
    'num_epochs': 30,
    'batch_size': 50,
    'learning_rate': 1e-3
}

loads = [
    'Air_Conditioner1_int_DB',
    'Microwave_int_DB',
    'Toaster_int_DB',
    'Lamp_int_DB',
    'AC_motor_DB',
    'INVERTER_13_1PH_DB',
    'AC_motor_4_37A_load_DB',
    'Air_Conditioner2_int_DB'
]

# Generating a synthetic signal,
# path - a folder where the signal will be saved
# n - signal index
# states - number of states incase of a changing state appliance
def gen_I(path, n=1, states=1):
    state_interval = 5
    harmony_n = np.random.randint(2,8)
    f = np.array([1, 3, 5, 7, 9, 11, 13]) * 50  # frequency space
    F = [None] * states
    P = [None] * states
    A = [None] * states

    # ------ Signal properties ------ #
    for i in range(0, states):
        F[i] = np.sort(np.random.choice(f, harmony_n, replace=False))                                # frequency vector
        P[i] = np.random.uniform(-1 / 2 * np.pi, 1 / 2 * np.pi, harmony_n)                           # phase vector
        A[i] = np.sort(np.random.randint(1, 10, size=harmony_n))[::-1]                               # amplitude vector

    # ------ Generate Signal ------ #
    Fs = preproc_config['Fs']                                                                 # sampling rate
    Ts = 1.0 / Fs                                                                             # sampling interval
    T_fin = 100                                                                                  # total time
    t = np.arange(0, T_fin, Ts)                                                               # time vector
    I_t_pre = [None]*states

    for j in range(0, states):
        I_t_pre[j] = np.array([np.sin(2 * np.pi * F[j] * t[i] + P[j]) for i in range(0, np.size(t))]).dot(A[j])

    samples = len(I_t_pre[0])
    step = samples//state_interval
    I_t = np.array([])
    for i in range(0, samples, step):                                                         # signal creation
        state = np.random.randint(0, states)
        I_t = np.concatenate((I_t, (I_t_pre[state])[i:i+step]))

    on = np.ones((T_fin * Fs), dtype=int)
    # ------ Determine on/off ------ #
    #on = np.sort(np.random.choice(T_fin*Fs-1, 16, replace=False))
    # label = np.ones((T_fin*Fs))
    # for i in range(0,np.size(on),2):
    #     I_t[on[i]:on[i+1]] = 0
    #     label[on[i]:on[i+1]] = 0

    # ------ Old labeling ------ #
    for i in range(0, (T_fin*Fs), int(T_fin*Fs/(2**n))*2):
        on[i:i+int(T_fin*Fs/(2**n))] = 0
    label = on


    # ------ Labeling data ------ #
    # i = step = 0
    # curr = np.random.randint(0, 2)
    # samples = T_fin*Fs
    # while i < samples:
    #     step = np.random.randint(samples // 16, samples // 3)
    #     on[i:i + step] = int(curr)
    #     curr = not curr           # toggle
    #     i += step           # step increment

    label = on
    I_t = I_t*on

    save_signal(n, I_t, label, path, F, A, P)
    return I_t, label

# Generates a main signal which is a summary of a few generated signals
# path - a folder where the signal will be saved
# n - number of appliances
def gen_sum(path, n):
    S_sum, label_sum = gen_I(path)
    for i in range(2, n+1):
        #states = np.random.randint(1, 5)
        states = 1
        temp_sum, temp_label = gen_I(path, n=i, states=states)
        S_sum += temp_sum
        label_sum = np.vstack((label_sum,temp_label))

    np.savetxt(path+"signal_sum_val.txt", S_sum, fmt='%.7f', delimiter='\n')
    np.savetxt(path+"signal_sum_label.txt", np.transpose(label_sum), fmt='%i', delimiter=',')

def gen_sum_measured(path):
    lst='Signal made from the following loads:\n'+loads[0]+'\n'
    I_sum = np.loadtxt(path+'val_'+loads[0]+'.txt')
    label_sum = np.loadtxt(path + 'label_' + loads[0] + '.txt')
    for i in range(1,nn_config['num_classes']):
        lst += loads[i]+'\n'
        I_temp = np.loadtxt(path + 'val_' + loads[i] + '.txt')
        temp_label = np.loadtxt(path + 'label_' + loads[i] + '.txt')
        I_sum += I_temp
        label_sum = np.vstack((label_sum, temp_label))

    np.savetxt(path+"signal_sum_val.txt", I_sum, fmt='%.7f', delimiter='\n')
    np.savetxt(path+"signal_sum_label.txt", np.transpose(label_sum), fmt='%i', delimiter=',')
    f = open(path + "signal_sum_loads.txt", 'w+')
    f.write(lst)
    f.close()


# Generate summarized signal from measured loads
# including every load configuration possible
# For example:
# the load for the label 1,0,0,1,0 will appear in I_sum[bin(10010)*sig_len):(1+bin(10010))*sig_len)]
def gen_sum_measured_syn(path):
    num_classes = nn_config['num_classes']
    I_signals = np.array([np.loadtxt(path + loads[i] + '.txt') for i in range(0, num_classes)])
    sig_len = np.shape(I_signals)[1]

    I_sum = np.zeros(sig_len*(2**num_classes))
    I_sum_label = np.zeros((sig_len*(2**num_classes),num_classes))
    for i in range(1,2**num_classes):
        # Create a binary representation of i as an array
        comb = np.array(list(np.binary_repr(i, num_classes)), dtype=int)

        # Sum the signals in the combination into I_sum
        I_sum[i*sig_len:(i + 1)*sig_len] = I_signals[np.where(comb == 1)].sum(axis=0)
        I_sum_label[i*sig_len:(i + 1)*sig_len,:] = comb

    np.savetxt(path+"signal_sum_val.txt", I_sum, fmt='%.7f', delimiter='\n')
    np.savetxt(path+"signal_sum_label.txt", I_sum_label, fmt='%i', delimiter=',')


def save_signal(i, I, label, path, F, A, P):
    np.savetxt(path+"signal_{}_val.txt".format(i), I, fmt='%.7f', delimiter='\n')
    np.savetxt(path+"signal_{}_label.txt".format(i), label, fmt='%i', delimiter='\n')
    states=len(F)
    f = open(path+"signal_{}_prop.txt".format(i), 'a+')
    f.seek(0)
    f.truncate()
    if states > 1:
        f.write("Multi State Load\n")
    for i in range(0,states):
        s = "State no." + str(i + 1)+"\n"
        f.write(s)
        np.savetxt(f, (F[i], A[i], P[i]), fmt='%.3f', delimiter=',')
    f.close()


def load_signal(i, folder_name):
    F, A, P = np.loadtxt(folder_name + "signal_{}_prop.txt".format(i), delimiter=',')
    I = np.loadtxt(folder_name + "signal_{}_val.txt".format(i))
    return F, A, P, I


def load_sum(folder_name):
    I = read_csv(folder_name + "signal_sum_val.txt", header=None).values.flatten()
    I_label = read_csv(folder_name + "signal_sum_label.txt", sep=',', header=None).values
    return I, I_label


def compare_input(I1,I2):
    return np.sqrt(((I1 - I2)**2).sum())


def plot_signal(s_path, index=-1):
    label_path = s_path.replace('_val', '_label')
    sample_win = int(preproc_config['Fs']*preproc_config['sample_time'])//5
    # I = np.loadtxt(s_path)
    # I_label = np.loadtxt(label_path, delimiter=',')
    I = read_csv(s_path, header=None).values.flatten()
    I_label = read_csv(label_path, sep=',', header=None).values

    if index > (len(I)-sample_win-1):
        print('index inserted is not valid')
        return 1
    if index < 0:
        index = np.random.randint(0,(len(I)-sample_win-1))
    if not('sum' in s_path):
        for i in range(index, (len(I)-sample_win-1)):
            if I_label[i] == 1:
                index = i
                break

    sampled_I = I[index:index+sample_win]
    #sampled_I = I[16876:16930]
    #sampled_label = I_label[index:index+sample_win]

    I_fft = fft(sampled_I,noise=preproc_config['noise'])
    I_fft_amp, I_fft_phase = fft_amp_phase(I_fft)

    #temp = fft2input(I_fft_amp, I_fft_phase,preproc_config['Fs'])

    n = len(sampled_I)                # length of the signal
    k = np.arange(n)
    T = n/preproc_config['Fs']
    frq = k/T
    frq = frq[range(int(n/2))]

    # Plot Signal
    fig1 = plt.figure()
    p1 = fig1.add_subplot(111)
    p1.plot(range(n), sampled_I, 'b')
    p1.set_title('Generated Sum signal')
    p1.set_xlabel('Time')
    p1.set_ylabel('I[A]')

    # Plot Amplitudes and Phase
    # Amplitude
    fig2 = plt.figure()
    p2 = fig2.add_subplot(121)
    p2.plot(frq, I_fft_amp, 'r.')
    p2.vlines(frq, [0], I_fft_amp)
    p2.grid(True)
    p2.set_title('Amplitudes by frequency of current signal - Noise 50%')
    p2.set_xlabel('Frequency[Hz]')
    p2.set_ylabel('|A|')
    # Phase
    p3 = fig2.add_subplot(122)
    p3.plot(frq, I_fft_phase, 'r.')
    # p3.vlines(frq,[0],I_fft_amp)
    p3.grid(True)
    p3.set_title('Phase by frequency of current signal - Noise 50%')
    p3.set_xlabel('Frequency[Hz]')
    p3.set_ylabel('Degree[$^\circ$]')

    plt.show()

def plot_signal_gui(sampled_I):
    I_fft = fft(sampled_I,noise=preproc_config['noise'])
    I_fft_amp, I_fft_phase = fft_amp_phase(I_fft)

    n = len(sampled_I)                # length of the signal
    k = np.arange(n)
    T = n/preproc_config['Fs']
    frq = k/T
    frq = frq[range(int(n/2))]

    # Plot Signal
    fig1 = plt.figure()
    p1 = fig1.add_subplot(131)
    p1.plot(range(n), sampled_I, 'b')
    p1.set_title('Signal')
    p1.set_xlabel('Time')
    p1.set_ylabel('I[A]')

    # Plot Amplitudes and Phase
    # Amplitude
    p2 = fig1.add_subplot(132)
    p2.plot(frq, I_fft_amp, 'r.')
    p2.vlines(frq, [0], I_fft_amp)
    p2.grid(True)
    p2.set_title('Amplitudes by frequency of signal')
    p2.set_xlabel('Frequency[Hz]')
    p2.set_ylabel('|A|')
    # Phase
    p3 = fig1.add_subplot(133)
    p3.plot(frq, I_fft_phase, 'r.')
    # p3.vlines(frq,[0],I_fft_amp)
    p3.grid(True)
    p3.set_title('Phase by frequency of signal')
    p3.set_xlabel('Frequency[Hz]')
    p3.set_ylabel('Degree[$^\circ$]')

    plt.show()
