import math
import numpy as np
import pandas as pd


class Layer:

    def __init__(self):
        self._name = 0

    def init(self, name):
        self._name = name

    def __str__(self):
        return f'Layer: {self._name}'
    
    def __repr__(self):
        return f'Layer: {self._name}'


class Dense(Layer):

    def __init__(self, inputs=1, outputs=1, activation='sigmoid'):
        super().__init__()
        self.W = np.random.rand(inputs, outputs) * np.sqrt(2 / (outputs + inputs))
        self.B = np.zeros((1, outputs))
        self.A = np.zeros((inputs, self.W.shape[0]))
        
        if activation == 'sigmoid':
            self._activation = self._sigmoid
        elif activation == 'relu':
            self._activation = self._relu
        elif activation == 'tahn':
            self._activation = self._tahn
        elif activation == 'softmax':
            self._activation = self._softmax

    def _sigmoid(self, Z, deriv=False):
        if deriv:
            return Z * (1 - Z)
        return 1. / (1 + np.exp(-Z))
    
    def _relu(self, Z, deriv=False):
        if deriv:
            return 1. * (Z > 0)
        return np.maximum(0, Z)

    def _tahn(self, Z, deriv=False):
        K = np.tanh(Z)
        if deriv:
            return 1 - (K**2)
        return K

    def _softmax(self, Z, deriv=False):
        y = np.exp(Z - Z.max())
        return y / np.sum(y, axis=1, keepdims=True)

    def forward(self, Z):
        self.A = self._activation(Z.dot(self.W) + self.B)
        return self.A

    def gradient(self, error):
        # Avoid exploding gradients
        return np.clip(error * self._activation(self.A, deriv=True), -1, 1)



class NeuralNetwork:

    def __init__(self, layers, X, y, loss='MSE'):
        # That is why we seed the generator - to make sure that we always get the same random numbers.
        np.random.seed(0)
        
        # Naming the layers (indexing)
        self._total_layers = len(layers)
        for k in range(self._total_layers):
            layers[k].init(k)

        # Initialization
        self._layers = layers
        self._X = X
        self._y = y
        
        self._loss = self._mse
        if loss == 'cross_entropy':
            self._loss = self._cross_entropy
        self._y = self._one_hot_encode(self._y)
        
        self._total_samples = 1. / self._y.shape[0]
        self._mem_weights = {}

    def predict(self, Z):
        return np.argmax(self._forward(Z), axis=1)

    def _one_hot_encode(self, y):
        return pd.get_dummies(y).values
    
    def _mse(self, y, E):
        return np.sum(E**2) * self._total_samples

    def _cross_entropy(self, y, E):
        E = E.clip(min=1e-12)
        # y = self._y
        return -(np.sum(y * np.log(E) + (1-y) * np.log(1-E))) * self._total_samples
    
    def _forward(self, Z):
        for i, layer in enumerate(self._layers):
            Z = layer.forward(Z)
        return Z

    def _backward(self, X, E_prev):
        # First Layer
        last_layer = self._layers[-1]
        delta = E_prev
        self._mem_weights[f'{last_layer}'] = (
            self._layers[-2].A.T.dot(delta),  # dW 
            np.sum(delta, axis=0)  # dB
        )

        # Hidden Layers
        k = len(self._layers)-2
        for layer in reversed(self._layers[1:len(self._layers)-1]):
            E_prev = E_prev.dot(last_layer.W.T)
            last_layer = layer
            delta = last_layer.gradient(E_prev)
            self._mem_weights[f'{last_layer}'] = (
                self._layers[(k-1)].A.T.dot(delta),  # dW 
                np.sum(delta, axis=0)  # dB
            )
            k -= 1

        # Last Layer
        E_prev = E_prev.dot(last_layer.W.T)
        last_layer = self._layers[0]
        delta = last_layer.gradient(E_prev)
        self._mem_weights[f'{last_layer}'] = (
            X.T.dot(delta),  # dW
            np.sum(delta, axis=0)  # dB
        )

    def _update_weights(self, lr):
        for layer in reversed(self._layers):
            W, B = self._mem_weights[f'{layer}']
            layer.W -= lr * (W * self._total_samples)
            layer.B -= lr * (B * self._total_samples)

    def _shuffle(self, X, y):
        permutation = np.random.permutation(X.shape[0])
        return X[permutation], y[permutation]

    def train(self, epochs=1500, lr=1e-3, batch_size=32):
        error_step = []
        total_expected_error = 0

        # Batch size iteration
        mb = math.ceil(self._X.shape[0] / batch_size)

        for ep, epoch in enumerate(range(epochs)):
            # Shuffle dataset in each epoch
            X, y = self._shuffle(self._X.copy(), self._y.copy())

            # Mini-batch
            total_error = 0
            k = 0
            for _ in range(mb):
                # Cropping
                ini = k * batch_size
                end = (k + 1) * batch_size
                cX = X[ini:end, :].copy()
                cy = y[ini:end, :].copy()
                k += 1

                # Forward
                Z = self._forward(cX)
                
                # Loss
                E = Z - cy  # error
                
                # Backward / Backprop
                self._backward(cX, E)

                # Update weights and bias
                self._update_weights(lr)

                # Cost
                total_error += self._loss(cy, E)

            if np.abs(total_expected_error-total_error) < 1e-8:
                return np.array(error_step)
            total_expected_error = total_error
            error_step.append(total_error)
        return np.array(error_step)
