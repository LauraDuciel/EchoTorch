# -*- coding: utf-8 -*-
#
# File : echotorch/nn/ESN.py
# Description : An Echo State Network module.
# Date : 26th of January, 2018
#
# This file is part of EchoTorch.  EchoTorch is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# Copyright Nils Schaetti, University of Neuchâtel <nils.schaetti@unine.ch>

"""
Created on 26 January 2018
@author: Nils Schaetti
"""

# Imports
import torch.sparse
import torch
import torch.nn as nn
from torch.autograd import Variable
from . import ESNCell
from RRCell import RRCell


# Stacked Echo State Network module
class StackedESN(nn.Module):
    """
    Stacked Echo State Network module
    """

    # Constructor
    def __init__(self, input_dim, hidden_dim, output_dim, spectral_radius=0.9, bias_scaling=0, input_scaling=1.0,
                 w=None, w_in=None, w_bias=None, w_fdb=None, sparsity=None, input_set=[1.0, -1.0], w_sparsity=None,
                 nonlin_func=torch.tanh, learning_algo='inv', ridge_param=0.0, create_cell=True,
                 feedbacks=False, with_bias=True, wfdb_sparsity=None, normalize_feedbacks=False):
        """
        Constructor
        :param input_dim: Inputs dimension.
        :param hidden_dim: Hidden layer dimension
        :param output_dim: Reservoir size
        :param spectral_radius: Reservoir's spectral radius
        :param bias_scaling: Scaling of the bias, a constant input to each neuron (default: 0, no bias)
        :param input_scaling: Scaling of the input weight matrix, default 1.
        :param w: Internation weights matrix
        :param w_in: Input-reservoir weights matrix
        :param w_bias: Bias weights matrix
        :param w_fdb: Feedback weights matrix
        :param sparsity:
        :param input_set:
        :param w_sparsity:
        :param nonlin_func: Reservoir's activation function (tanh, sig, relu)
        :param learning_algo: Which learning algorithm to use (inv, LU, grad)
        """
        super(StackedESN, self).__init__()

        # Properties
        self.n_layers = len(hidden_dim)
        self.esn_layers = list()

        # Number of features
        self.n_features = 0

        # Recurrent layer
        for n in range(self.n_layers):
            # Input dim
            layer_input_dim = input_dim if n == 0 else hidden_dim[n-1]
            self.n_features += layer_input_dim

            # Parameters
            layer_spectral_radius = spectral_radius[n] if type(spectral_radius) is list else spectral_radius
            layer_bias_scaling = bias_scaling[n] if type(bias_scaling) is list else bias_scaling
            layer_input_scaling = input_scaling[n] if type(input_scaling) is list else input_scaling

            # W
            if type(w) is torch.Tensor and w.ndim == 3:
                layer_w = w[n]
            elif type(w) is torch.Tensor:
                layer_w = w
            else:
                layer_w = None
            # end if

            # W in
            if type(w_in) is torch.Tensor and w_in.ndim == 3:
                layer_w_in = w_in[n]
            elif type(w_in) is torch.Tensor:
                layer_w_in = w_in
            else:
                layer_w_in = None
            # end if

            # W bias
            if type(w_bias) is torch.Tensor and w_bias.ndim == 2:
                layer_w_bias = w_bias[n]
            elif type(w_bias) is torch.Tensor:
                layer_w_bias = w_bias
            else:
                layer_w_bias = None
            # end if

            # Parameters

            self.esn_layers.append(ESNCell(
                layer_input_dim, hidden_dim[n], layer_spectral_radius, layer_bias_scaling, layer_input_scaling,
                layer_w, layer_w_in, layer_w_bias, None, sparsity, input_set, w_sparsity, nonlin_func, feedbacks, output_dim, wfdb_sparsity, normalize_feedbacks
            ))
        # end for

        # Output layer
        self.output = RRCell(self.n_features, output_dim, ridge_param, feedbacks, with_bias, learning_algo)
    # end __init__

    ###############################################
    # PROPERTIES
    ###############################################

    # Hidden layer
    @property
    def hidden(self):
        """
        Hidden layer
        :return:
        """
        return self.esn_cell.hidden
    # end hidden

    # Hidden weight matrix
    @property
    def w(self):
        """
        Hidden weight matrix
        :return:
        """
        return self.esn_cell.w
    # end w

    # Input matrix
    @property
    def w_in(self):
        """
        Input matrix
        :return:
        """
        return self.esn_cell.w_in
    # end w_in

    ###############################################
    # PUBLIC
    ###############################################

    # Reset learning
    def reset(self):
        """
        Reset learning
        :return:
        """
        # Reset output layer
        self.output.reset()

        # Training mode again
        self.train(True)
    # end reset

    # Output matrix
    def get_w_out(self):
        """
        Output matrix
        :return:
        """
        return self.output.w_out
    # end get_w_out

    # Set W
    def set_w(self, w):
        """
        Set W
        :param w:
        :return:
        """
        self.esn_cell.w = w
    # end set_w

    # Forward
    def forward(self, u, y=None):
        """
        Forward
        :param u: Input signal.
        :param y: Target outputs
        :return: Output or hidden states
        """
        # Compute hidden states
        if self.feedbacks and self.training:
            hidden_states = self.esn_cell(u, y)
        elif self.feedbacks and not self.training:
            hidden_states = self.esn_cell(u, w_out=self.w_out)
        else:
            hidden_states = self.esn_cell(u)
        # end if

        # Learning algo
        return self.output(hidden_states)
    # end forward

    # Finish training
    def finalize(self):
        """
        Finalize training with LU factorization
        """
        # Finalize output training
        self.output.finalize()

        # Not in training mode anymore
        self.train(False)
    # end finalize

    # Reset hidden layer
    def reset_hidden(self):
        """
        Reset hidden layer
        :return:
        """
        self.esn_cell.reset_hidden()
    # end reset_hidden

    # Get W's spectral radius
    def get_spectral_radius(self):
        """
        Get W's spectral radius
        :return: W's spectral radius
        """
        return self.esn_cell.get_spectral_raduis()
    # end spectral_radius

# end ESNCell
