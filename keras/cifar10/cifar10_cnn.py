# -- coding: utf8 --
'''Train a simple deep CNN on the CIFAR10 small images dataset.

GPU run command with Theano backend (with TensorFlow, the GPU is automatically used):
    THEANO_FLAGS=mode=FAST_RUN,device=gpu,floatx=float32 python cifar10_cnn.py

It gets down to 0.65 test logloss in 25 epochs, and down to 0.55 after 50 epochs.
(it's still underfitting at that point, though).
'''

from __future__ import print_function

import argparse
import os

import missinglink
from keras.callbacks import ModelCheckpoint, ReduceLROnPlateau, TensorBoard, EarlyStopping
from keras_sequential_ascii import keras2ascii

from data_iterator import process_file_and_metadata
from metrics_callback import Metrics, IntervalEvaluation
from model import get_model
from test_callback import TestCallback
from utils import safe_make_dirs

parser = argparse.ArgumentParser(description='Cifar10 Data Iterator Sample')

parser.add_argument('--datavolume', required=False)
parser.add_argument('--query', required=False)
parser.add_argument('--owner-id', required=True)
parser.add_argument('--project-token', required=True)
parser.add_argument('--processes', type=int, required=False, default=200)
parser.add_argument('--epochs', type=int, default=10)
parser.add_argument('--batch-size', type=int, default=32)
parser.add_argument('--num-predictions', type=int, default=20)
parser.add_argument('--model', required=False, type=str, default='cifar10')

args = parser.parse_args()

DATAVOLUME = args.datavolume
QUERY = args.query
OWNER_ID = args.owner_id
PROJECT_TOKEN = args.project_token
class_mapping = {
    0: 'airplane',
    1: 'automobile',
    2: 'bird',
    3: 'cat',
    4: 'deer',
    5: 'dog',
    6: 'frog',
    7: 'horse',
    8: 'ship',
    9: 'truck'
}
missinglink_callback = missinglink.KerasCallback(owner_id=OWNER_ID, project_token=PROJECT_TOKEN)

missinglink_callback.set_properties("CIFAR10-CNN", class_mapping=class_mapping)

batch_size = args.batch_size
num_classes = 10
epochs = args.epochs
data_augmentation = True
num_predictions = args.num_predictions

save_dir = os.path.join('/output' if missinglink_callback.rm_data_iterator_settings else os.getcwd(), 'saved_models')
model_name = 'keras_cifar10_trained_model.h5'

model = get_model()

model.summary()

keras2ascii(model)


print('Using real-time data augmentation.')

checkpoint_path = 'ssd7_weights_epoch-{epoch:02d}_loss-{loss:.4f}.h5'
tensor_board_path = 'tensorboard'
if missinglink_callback.rm_active:
    directory = '/output/checkpoints'
    safe_make_dirs(directory)
    checkpoint_path = os.path.join(directory, checkpoint_path)
    tensor_board_path = os.path.join('/output', tensor_board_path)

iterator_settings = missinglink_callback.rm_data_iterator_settings
if iterator_settings is not None:
    volume_id = iterator_settings[0]
    query = iterator_settings[1]
else:
    volume_id = DATAVOLUME
    query = QUERY

data_generator = missinglink_callback.bind_data_generator(
    volume_id, query, process_file_and_metadata, batch_size=batch_size, processes=args.processes
)

# given the query has a @split directive it will return a number of generator as the number of splits.
train_generator, test_generator = data_generator.flow()

test_callback = TestCallback(test_generator, missinglink_callback, batch_size)
metrics_callback = Metrics()
interval_metrics = IntervalEvaluation(missinglink_callback)

missinglink_callback.set_hyperparams(batch_size=batch_size,
                                     steps_per_epoch=len(train_generator),
                                     validation_steps=len(test_generator),
                                     processes=args.processes)

# Fit the model on the batches generated by datagen.flow().
model.fit_generator(train_generator,
                    steps_per_epoch=len(train_generator),
                    epochs=epochs,
                    validation_data=test_generator,
                    validation_steps=len(test_generator),
                    workers=4,
                    callbacks=[missinglink_callback, test_callback, interval_metrics,
                               ModelCheckpoint(
                                   checkpoint_path,
                                   monitor='val_loss',
                                   verbose=1,
                                   save_best_only=True,
                                   save_weights_only=True,
                                   mode='auto',
                                   period=5
                               ),
                               EarlyStopping(monitor='val_acc', min_delta=1e-4, patience=20),
                               ReduceLROnPlateau(
                                   monitor='val_loss',
                                   factor=0.1,
                                   patience=10,
                                   epsilon=0.001,
                                   cooldown=0,
                                   verbose=1
                               ),
                               TensorBoard(log_dir=tensor_board_path)

                               ])

# Save model and weights
if not os.path.isdir(save_dir):
    os.makedirs(save_dir)
model_path = os.path.join(save_dir, model_name)
model.save(model_path)
print('Saved trained model at %s ' % model_path)

# Load label names to use in prediction results
# label_list_path = 'datasets/cifar-10-batches-py/batches.meta'
#
# keras_dir = os.path.expanduser(os.path.join('~', '.keras'))
# datadir_base = os.path.expanduser(keras_dir)
# if not os.access(datadir_base, os.W_OK):
#     datadir_base = os.path.join('/tmp', '.keras')
# label_list_path = os.path.join(datadir_base, label_list_path)

# with open(label_list_path, mode='rb') as f:
#     labels = pickle.load(f)
#
# predict_gen = model.predict_generator(datagen.flow(x_test, y_test,
#                                                    batch_size=batch_size,
#                                                    shuffle=False),
#                                       steps=x_test.shape[0] // batch_size,
#                                       workers=4)
#
# for predict_index, predicted_y in enumerate(predict_gen):
#     actual_label = labels['label_names'][np.argmax(y_test[predict_index])]
#     predicted_label = labels['label_names'][np.argmax(predicted_y)]
#     print('Actual Label = %s vs. Predicted Label = %s' % (actual_label,
#                                                           predicted_label))
#     if predict_index == num_predictions:
#         break
