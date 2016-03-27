# -*- coding: UTF-8 -*-
import sys
import os
import pickle
import numpy as np
import tensorflow as tf

BATCH_SIZE = 45
KERNEL_SIZE = 5
CHANNELS = 1
DEPTH = 32
HIDDEN_NUM = 256
EPOCHS = 5000


def train(datasets, params):
    train, train_lbl = datasets['train'], datasets['train_lbl']
    valid, valid_lbl = datasets['valid'], datasets['valid_lbl']

    graph, x, y_, preds, loss = params

    with tf.Session(graph=graph) as session:
        # create the optimizer to minimize the loss
        #optimizer = tf.train.GradientDescentOptimizer(0.005).minimize(loss)
        optimizer = tf.train.AdamOptimizer(1e-4).minimize(loss)

        correct_prediction = tf.equal(tf.argmax(preds, 1), tf.argmax(y_, 1))
        accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))

        session.run(tf.initialize_all_variables())
        for step in range(EPOCHS):
            offset = (step * BATCH_SIZE) % (train_lbl.shape[0] - BATCH_SIZE)
            batch_data = train[offset:(offset+BATCH_SIZE), :, :, :]
            batch_labels = train_lbl[offset:(offset+BATCH_SIZE), :]

            feed_dict={x: batch_data, y_: batch_labels}
            optimizer.run(feed_dict=feed_dict)

            if step % 10 == 0:
                train_accuracy = accuracy.eval(feed_dict=feed_dict)
                print("step %d, training accuracy %g" % (step, train_accuracy))
                valid_accuracy = accuracy.eval(
                    feed_dict={x: valid, y_: valid_lbl})
                print("step %d, valid accuracy %g" % (step, valid_accuracy))

    print 'Done'


def build_model(size, nlabels):

    def weight(shape):
        return tf.Variable(tf.truncated_normal(shape, stddev=0.1))

    def bias(shape):
        return tf.Variable(tf.constant(0.1, shape=shape))

    def conv2d(x, W):
        return tf.nn.conv2d(x, W, strides=[1, 1, 1, 1], padding='SAME')

    def max_pool(x):
        return tf.nn.max_pool(x, ksize=[1, 2, 2, 1],
                              strides=[1, 2, 2, 1], padding='SAME')

    graph = tf.Graph()
    with graph.as_default():
        # placeholders for input, None means batch of any size
        x = tf.placeholder(tf.float32, shape=(None, size, size, CHANNELS))
        y_ = tf.placeholder(tf.float32, shape=(None, nlabels))

        # create weights and biases for the 1st conv layer
        layer1_weights = weight([KERNEL_SIZE, KERNEL_SIZE, CHANNELS, DEPTH]) 
        layer1_biases = bias([DEPTH])

        # convolve input with the first kernels and apply relu
        h_conv1 = tf.nn.relu(conv2d(x, layer1_weights) + layer1_biases)
        # max-pool
        h_pool1 = max_pool(h_conv1)

        # create weights and biases for the 2nd conv layer
        layer2_weights = weight([KERNEL_SIZE, KERNEL_SIZE, DEPTH, DEPTH*2])
        layer2_biases = bias([DEPTH*2])

        # convolve first hidden layer output with the second kernels and apply relu
        h_conv2 = tf.nn.relu(conv2d(h_pool1, layer2_weights) + layer2_biases)
        # max-pool
        h_pool2 = max_pool(h_conv2)

        # create weights and biases for the 3rd hidden layer
        layer3_weights = weight([size*size // 16 * DEPTH * 2, HIDDEN_NUM])
        layer3_biases = bias([HIDDEN_NUM])

        # fully connect the 2nd layer output to 3rd input
        dim = h_pool2.get_shape().as_list()
        reshape = tf.reshape(h_pool2, [-1, dim[1]*dim[2]*dim[3]])
        hidden = tf.nn.relu(tf.matmul(reshape, layer3_weights) + layer3_biases)

        # create weights and biases for the output layer
        layer4_weights = weight([HIDDEN_NUM, nlabels])
        layer4_biases = bias([nlabels])

        # predict from logits using softmax
        logits = tf.matmul(hidden, layer4_weights) + layer4_biases
        predictions = tf.nn.softmax(logits)

        # cross-entropy as the loss
        loss = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(logits, y_))


        return (graph, x, y_, predictions, loss)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print "Usage: python {} datasets.pickle".format(sys.argv[0])
        print """
Load the pickled datasets, train and evaluate the convolutional neural network,
then pickle and save it."""
        sys.exit(1)

    try:
        datasets = None
        with open(sys.argv[1], 'rb') as f:
            datasets = pickle.load(f)
        if len(datasets['train']) == 0:
            raise ValueError
    except IOError:
        print 'Failed to load dataset {}'.format(sys.argv[1])
    except ValueError:
        print 'Empty train dataset {}'.format(sys.argv[1])

    sx, sy, _ = datasets['train'][0].shape
    if sx != sy:
        raise ValueError('Input train data not a square')

    nlabels = len(datasets['label_map'])
    model_params = build_model(sx, nlabels)
    train(datasets, model_params)
