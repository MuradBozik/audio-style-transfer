import numpy as np
from training.networks import build_siamese, build_generator, build_critic
from tensorflow.keras.optimizers import Adam
import matplotlib.pyplot as plt
import soundfile as sf
import IPython
import os
from utils.common import Common_helpers
from utils.inversion import Inversion_helpers


class Training_helpers():
    def __init__(self, args, aspec):
        self.args = args
        self.aspec = aspec
        self.IH = Inversion_helpers(args)
        self.CH = Common_helpers(args)

    # Load past models from path to resume training or test
    def load(self, path):
        gen = build_generator((self.args.hop, self.args.shape, 1))
        siam = build_siamese((self.args.hop, self.args.shape, 1))
        critic = build_critic((self.args.hop, 3 * self.args.shape, 1))
        gen.load_weights(path + '/gen.h5')
        critic.load_weights(path + '/critic.h5')
        siam.load_weights(path + '/siam.h5')
        return gen, critic, siam

    # Build models

    def build(self):
        gen = build_generator((self.args.hop, self.args.shape, 1))
        siam = build_siamese((self.args.hop, self.args.shape, 1))
        # the discriminator accepts as input spectrograms of triple the width of those generated by the generator
        critic = build_critic((self.args.hop, 3 * self.args.shape, 1))
        return gen, critic, siam

    # Generate a random batch to display current training results

    def testgena(self):
        sw = True
        while sw:
            a = np.random.choice(self.aspec)
            if a.shape[1] // self.args.shape != 1:
                sw = False
        dsa = []
        if a.shape[1] // self.args.shape > 6:
            num = 6
        else:
            num = a.shape[1] // self.args.shape
        rn = np.random.randint(a.shape[1] - (num * self.args.shape))
        for i in range(num):
            im = a[:, rn + (i * self.args.shape):rn + (i * self.args.shape) + self.args.shape]
            im = np.reshape(im, (im.shape[0], im.shape[1], 1))
            dsa.append(im)
        return np.array(dsa, dtype=np.float32)

    # Show results mid-training
    def save_test_image_full(self, path, ipython=False):
        a = self.testgena()
        print(a.shape)
        ab = self.gen(a, training=False)
        ab = self.CH.testass(ab)
        a = self.CH.testass(a)
        abwv = self.IH.deprep(ab)
        awv = self.IH.deprep(a)
        sf.write(path + '/new_file.wav', abwv, self.args.sr)
        if ipython:
            IPython.display.display(IPython.display.Audio(np.squeeze(abwv), rate=self.args.sr))
            IPython.display.display(IPython.display.Audio(np.squeeze(awv), rate=self.args.sr))
        fig, axs = plt.subplots(ncols=2)
        axs[0].imshow(np.flip(a, -2), cmap=None)
        axs[0].axis('off')
        axs[0].set_title('Source')
        axs[1].imshow(np.flip(ab, -2), cmap=None)
        axs[1].axis('off')
        axs[1].set_title('Generated')
        plt.savefig(os.path.join(path, "spectrograms.png"), format='png')


    # Save in training loop
    # use custom save_path (i.e. Drive '../content/drive/My Drive/')
    def save_end(self, epoch, gloss, closs, mloss, n_save=3, save_path='../content/'):
        if epoch % n_save == 0:
            print('Saving...')
            path = f'{save_path}/MELGANVC-{str(gloss)[:9]}-{str(closs)[:9]}-{str(mloss)[:9]}'
            os.mkdir(path)
            self.gen.save_weights(path + '/gen.h5')
            self.critic.save_weights(path + '/critic.h5')
            self.siam.save_weights(path + '/siam.h5')
            self.save_test_image_full(path)

    # Get models and optimizers
    def get_networks(self, load_model=False, path=None):
        if not load_model:
            gen, critic, siam = self.build()
            print('Built networks')
        else:
            gen, critic, siam = self.load(path)
            print('Loaded networks')


        opt_gen = Adam(0.0001, 0.5)
        opt_disc = Adam(0.0001, 0.5)

        self.gen = gen
        self.critic = critic
        self.siam = siam
        self.opt_gen = opt_gen
        self.opt_disc = opt_disc

        return gen, critic, siam, [opt_gen, opt_disc]

    # Set learning rate
    def update_lr(self, lr):
        self.opt_gen.learning_rate = lr
        self.opt_disc.learning_rate = lr
