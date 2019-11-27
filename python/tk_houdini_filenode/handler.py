# Copyright (c) 2015 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

# built-ins
import base64
import os
import sys
import zlib
import shutil

try:
   import cPickle as pickle
except:
   import pickle

# houdini
import hou
import _alembic_hom_extensions as abc

# import pyseq
sys.path.append(r'\\server01\shared\sharedPython\modules\pyseq')
import pyseq

# toolkit
import sgtk

class TkFileNodeHandler(object):
    """Handle Tk file node operations and callbacks."""


    ############################################################################
    # Class data

    HOU_SOP_GEOMETRY_TYPE = "file"
    """Houdini type for file sops."""
    # this is correct. the houdini internal rop_file is a sop.

    NODE_OUTPUT_PATH_PARM = "filepath"
    """The name of the output path parameter on the node."""

    TK_FILE_NODE_TYPE = "sgtk_file"
    """The class of node as defined in Houdini for the file nodes."""

    TK_OUTPUT_CONNECTIONS_KEY = "tk_output_connections"
    """The key in the user data that stores the save output connections."""

    TK_OUTPUT_CONNECTION_CODEC = "sgtk-01"
    """The encode/decode scheme currently being used."""

    TK_OUTPUT_CONNECTION_CODECS = {
        "sgtk-01": {
            'encode': lambda data: \
                base64.b64encode(zlib.compress(pickle.dumps(data))),
            'decode': lambda data_str: \
                pickle.loads(zlib.decompress(base64.b64decode(data_str))),
        },
    }
    """Encode/decode schemes. To support backward compatibility if changes."""
    # codec names should not include a ":"

    ############################################################################
    # Class methods

    @classmethod
    def convert_back_to_tk_file_nodes(cls, app):
        """Convert file nodes back to Toolkit file nodes.

        :param app: The calling Toolkit Application

        Note: only converts nodes that had previously been Toolkit file
        nodes.

        """

        # get all sop file nodes in the session
        file_nodes = []
        file_nodes.extend(hou.nodeType(hou.sopNodeTypeCategory(),
            cls.HOU_SOP_GEOMETRY_TYPE).instances())

        if not file_nodes:
            app.log_debug("No file Nodes found for conversion.")
            return

        # the tk node type we'll be converting to
        tk_node_type = TkFileNodeHandler.TK_FILE_NODE_TYPE

        # iterate over all the file nodes and attempt to convert them
        for file_node in file_nodes:

            # get the user data dictionary stored on the node
            user_dict = file_node.userDataDict()

            # create a new, Toolkit file node:
            tk_file_node = file_node.parent().createNode(tk_node_type)

            # copy over all parameter values except the output path 
            _copy_parm_values(file_node, tk_file_node,
                excludes=[cls.NODE_OUTPUT_PATH_PARM])

            # copy the inputs and move the outputs
            _copy_inputs(file_node, tk_file_node)

            # determine the built-in operator type
            if file_node.type().name() == cls.HOU_SOP_GEOMETRY_TYPE:
                _restore_outputs_from_user_data(file_node, tk_file_node)

            # make the new node the same color. the profile will set a color, 
            # but do this just in case the user changed the color manually
            # prior to the conversion.
            tk_file_node.setColor(file_node.color())

            # remember the name and position of the original file node
            file_node_name = file_node.name()
            file_node_pos = file_node.position()

            # destroy the original file node
            file_node.destroy()

            # name and reposition the new, regular file node to match the
            # original
            tk_file_node.setName(file_node_name)
            tk_file_node.setPosition(file_node_pos)

            app.log_debug("Converted: file node '%s' to TK file node."
                % (file_node_name,))

    @classmethod
    def convert_to_regular_file_nodes(cls, app):
        """Convert Toolkit file nodes to regular file nodes.

        :param app: The calling Toolkit Application

        """

        tk_node_type = TkFileNodeHandler.TK_FILE_NODE_TYPE

        # determine the surface operator type for this class of node
        sop_types = hou.sopNodeTypeCategory().nodeTypes()
        sop_type = sop_types[tk_node_type]

        # determine the render operator type for this class of node
        rop_types = hou.ropNodeTypeCategory().nodeTypes()
        rop_type = rop_types[tk_node_type]

        # get all instances of tk file rop/sop nodes
        tk_file_nodes = []
        tk_file_nodes.extend(
            hou.nodeType(hou.sopNodeTypeCategory(), tk_node_type).instances())
        tk_file_nodes.extend(
            hou.nodeType(hou.ropNodeTypeCategory(), tk_node_type).instances())

        if not tk_file_nodes:
            app.log_debug("No Toolkit file Nodes found for conversion.")
            return

        # iterate over all the tk file nodes and attempt to convert them
        for tk_file_node in tk_file_nodes:

            # determine the corresponding, built-in operator type
            if tk_file_node.type() == sop_type:
                file_operator = cls.HOU_SOP_GEOMETRY_TYPE
            else:
                app.log_warning("Unknown type for node '%s': %s'" %
                    (tk_file_node.name(), tk_file_node.type()))
                continue

            # create a new, regular file node
            file_node = tk_file_node.parent().createNode(file_operator)

            # copy the file parms value to the new node
            filename = _get_output_menu_label(
                tk_file_node.parm(cls.NODE_OUTPUT_PATH_PARM))
            file_node.parm(cls.NODE_OUTPUT_PATH_PARM).set(filename)

            # copy across knob values
            _copy_parm_values(tk_file_node, file_node,
                excludes=[cls.NODE_OUTPUT_PATH_PARM])

            # store the file output profile name in the user data so that we
            # can retrieve it later.
            output_profile_parm = tk_file_node.parm(
                cls.TK_OUTPUT_PROFILE_PARM)

            # copy the inputs and move the outputs
            _copy_inputs(tk_file_node, file_node)
            if file_operator == cls.HOU_SOP_GEOMETRY_TYPE:
                _save_outputs_to_user_data(tk_file_node, file_node)

            # make the new node the same color
            file_node.setColor(tk_file_node.color())

            # remember the name and position of the original tk file node
            tk_file_node_name = tk_file_node.name()
            tk_file_node_pos = tk_file_node.position()

            # destroy the original tk file node
            tk_file_node.destroy()

            # name and reposition the new, regular file node to match the
            # original
            file_node.setName(tk_file_node_name)
            file_node.setPosition(tk_file_node_pos)

            app.log_debug("Converted: Tk file node '%s' to file node."
                % (tk_file_node_name,))

    @classmethod
    def get_all_tk_file_nodes(cls):
        """
        Returns a list of all tk-houdini-filenode instances in the current
        session.
        """

        tk_node_type = TkFileNodeHandler.TK_FILE_NODE_TYPE

        return hou.nodeType(hou.ropNodeTypeCategory(), tk_node_type).instances()

    @classmethod
    def get_output_path(cls, node):
        """
        Returns the evaluated output path for the supplied node.
        """

        output_parm = node.parm(cls.NODE_OUTPUT_PATH_PARM)
        path = hou.expandString(output_parm.evalAsString())
        return path

    ############################################################################
    # Instance methods

    def __init__(self, app):
        """Initialize the handler.
        
        :params app: The application instance. 
        
        """

        # keep a reference to the app for easy access to templates, settings,
        # logging methods, tank, context, etc.
        self._app = app


    ############################################################################
    # methods and callbacks executed via the OTLs

    # copy the render path for the current node to the clipboard
    def copy_path_to_clipboard(self):

        render_path = self._compute_output_path(hou.pwd())

        # use Qt to copy the path to the clipboard:
        from sgtk.platform.qt import QtGui
        QtGui.QApplication.clipboard().setText(render_path)

        self._app.log_debug(
            "Copied render path to clipboard: %s" % (render_path,))

    # refresh the output profile path
    def refresh_path(self, node):

        path = self._compute_output_path(node)
        self._check_alembic(node)
        self.check_seq(node)
        return path

    # open a file browser showing the render path of the current node
    def show_in_fs(self):

        # retrieve the calling node
        current_node = hou.pwd()
        if not current_node:
            return

        render_dir = None

        # first, try to just use the current cached path:
        render_path = self._compute_output_path(current_node)

        if render_path:
            # the above method returns houdini style slashes, so ensure these
            # are pointing correctly
            render_path = render_path.replace("/", os.path.sep)

            dir_name = os.path.dirname(render_path)
            if os.path.exists(dir_name):
                render_dir = dir_name

        # if we have a valid render path then show it:
        if render_dir:
            # TODO: move to utility method in core
            system = sys.platform

            # run the app
            if system == "linux2":
                cmd = "xdg-open \"%s\"" % render_dir
            elif system == "darwin":
                cmd = "open '%s'" % render_dir
            elif system == "win32":
                cmd = "cmd.exe /C start \"Folder\" \"%s\"" % render_dir
            else:
                msg = "Platform '%s' is not supported." % (system,)
                self._app.log_error(msg)
                hou.ui.displayMessage(msg)

            self._app.log_debug("Executing command:\n '%s'" % (cmd,))
            exit_code = os.system(cmd)
            if exit_code != 0:
                msg = "Failed to launch '%s'!" % (cmd,)
                hou.ui.displayMessage(msg)

    # called when the node is created.
    def setup_node(self, node):
        try:
            self._app.log_metric("Create", log_version=True)
        except:
            # ingore any errors. ex: metrics logging not supported
            pass

    def check_seq(self, node):
        path = node.parm('filepath').evalAsString()
        if node.parm('mode').evalAsString() == 'file':
            path = node.parm('filepath').unexpandedString()

        returnStr = None
        if '$F4' in path:
            path = path.replace('$F4', '*')
            sequences = pyseq.get_sequences(path)

            if len(sequences) == 1:
                seq = sequences[0]

                if seq:
                    if seq.missing():
                        returnStr = '[%s-%s], missing %s' % (seq.format('%s'), seq.format('%e'), seq.format('%m'))
                    else:
                        returnStr = seq.format('%R')
                else:
                    returnStr = 'Invalid Sequence Object!'
            else:
                returnStr = 'No or multiple sequences detected!'
        elif path.split('.')[-1] == 'abc':
            if os.path.exists(path):
                abcRange = abc.alembicTimeRange(path)
                        
                if abcRange:
                    returnStr = '[%s-%s] - ABC Archive' % (int(abcRange[0] * hou.fps()), int(abcRange[1] * hou.fps()))
                else:
                    returnStr = 'Single Abc'
            else:
                returnStr = 'No Cache!'
        else:
            if os.path.exists(path):
                returnStr = 'Single Frame'
            else:
                returnStr = 'No Cache!'

        node.parm('seqlabel').set(returnStr)

    def override_version(self, node):
        if node.parm('overver').evalAsInt():
            rop_node_path = node.parm('rop').evalAsString()

            if rop_node_path:
                path = node.parm('filepath').evalAsString()
                
                rop_node = hou.node(rop_node_path)
                template = rop_node.hm().app().handler.get_output_template(rop_node)
                
                fields = template.get_fields(path)
                node.parm('ver').set(fields['version'])
                node.parm('ver').pressButton()

                node.setComment('Version Overriden!')
                node.setGenericFlag(hou.nodeFlag.DisplayComment, True)
        else:
            node.setComment('')
            node.setGenericFlag(hou.nodeFlag.DisplayComment, False)
            
            self.refresh_path(node)



    ############################################################################
    # Private methods

    # compute the output path based on the current work file and cache template
    def _compute_output_path(self, node):
        mode = node.parm('mode').evalAsString()
    
        return_str = None
        if mode == 'file':
            return_str = node.parm('file').unexpandedString()
        elif mode == 'out':
            rop_node_path = node.parm('rop').evalAsString()
            
            if rop_node_path:
                rop_node = hou.node(rop_node_path)
                
                if rop_node and rop_node.type().name() == "sgtk_geometry":
                    if node.parm('overver').evalAsInt():
                        template = rop_node.hm().app().handler.get_output_template(rop_node)
                        path = rop_node.parm("sopoutput").evalAsString()

                        fields = template.get_fields(path).copy()
                        fields['version'] = node.parm('ver').evalAsInt()

                        return_str = template.apply_fields(fields)
                        return_str = return_str.replace(os.path.sep, "/")
                    else:
                        # set expression
                        expression = "chs('%s')" % rop_node.parm("sopoutput").path()
                        node.parm('filepath').setExpression(expression, language=hou.exprLanguage.Hscript)
                        return
                else:
                    return_str = 'Invalid Out node!'
            else:
                return_str = 'Missing Out path!'
        else:
            return_str = 'Mode not recognized!'
        
        node.parm('filepath').deleteAllKeyframes()
        node.parm('filepath').set(return_str)

        return return_str

    def _check_alembic(self, node):
        filepath = node.parm('filepath').evalAsString()
    
        if filepath.split('.')[-1] == 'abc':
            node.parm('isalembic').set(1)
        else:
            node.parm('isalembic').set(0)


################################################################################
# Utility methods

# Copy all the input connections from this node to the target node.
def _copy_inputs(source_node, target_node):

    input_connections = source_node.inputConnections()
    num_target_inputs = len(target_node.inputConnectors())

    if len(input_connections) > num_target_inputs:
        raise hou.InvalidInput(
            "Not enough inputs on target node. Cannot copy inputs from "
            "'%s' to '%s'" % (source_node, target_node)
        )
        
    for connection in input_connections:
        target_node.setInput(connection.inputIndex(),
            connection.inputNode())


# Copy parameter values of the source node to those of the target node if a
# parameter with the same name exists.
def _copy_parm_values(source_node, target_node, excludes=None):

    if not excludes:
        excludes = []

    # build a parameter list from the source node, ignoring the excludes
    source_parms = [
        parm for parm in source_node.parms() if parm.name() not in excludes]

    for source_parm in source_parms:

        source_parm_template = source_parm.parmTemplate()

        # skip folder parms
        if isinstance(source_parm_template, hou.FolderSetParmTemplate):
            continue

        target_parm = target_node.parm(source_parm.name())

        # if the parm on the target node doesn't exist, skip it
        if target_parm is None:
            continue

        # if we have keys/expressions we need to copy them all.
        if source_parm.keyframes():
            for key in source_parm.keyframes():
                target_parm.setKeyframe(key)
        else:
            # if the parameter is a string, copy the raw string.
            if isinstance(source_parm_template, hou.StringParmTemplate):
                target_parm.set(source_parm.unexpandedString())
            # copy the evaluated value
            else:
                try:
                    target_parm.set(source_parm.eval())
                except TypeError:
                    # The pre- and post-script type comboboxes changed sometime around
                    # 16.5.439 to being string type parms that take the name of the language
                    # (hscript or python) instead of an integer index of the combobox item
                    # that's selected. To support both, we try the old way (which is how our
                    # otl is setup to work), and if that fails we then fall back on mapping
                    # the integer index from our otl's parm over to the string language name
                    # that the file node is expecting.
                    if source_parm.name().startswith("lpre") or source_parm.name().startswith("lpost"):
                        value_map = ["hscript", "python"]
                        target_parm.set(value_map[source_parm.eval()])
                    else:
                        raise

# move all the output connections from the source node to the target node
def _move_outputs(source_node, target_node):

    for connection in source_node.outputConnections():
        output_node = connection.outputNode()
        output_node.setInput(connection.inputIndex(), target_node)

# saves output connections into user data of target node. Needed when target
# node doesn't have outputs.
def _save_outputs_to_user_data(source_node, target_node):

    output_connections = source_node.outputConnections()
    if not output_connections:
        return

    outputs = []
    for connection in output_connections:
        output_dict = {
            'node': connection.outputNode().path(),
            'input': connection.inputIndex(),
        }
        outputs.append(output_dict)

    # get the current encoder for the handler
    handler_cls = TkFileNodeHandler
    codecs = handler_cls.TK_OUTPUT_CONNECTION_CODECS
    encoder = codecs[handler_cls.TK_OUTPUT_CONNECTION_CODEC]['encode']

    # encode and prepend the current codec name
    data_str = handler_cls.TK_OUTPUT_CONNECTION_CODEC + ":" + encoder(outputs)

    # set the encoded data string on the input node
    target_node.setUserData(handler_cls.TK_OUTPUT_CONNECTIONS_KEY, data_str)

# restore output connections from this node to the target node.
def _restore_outputs_from_user_data(source_node, target_node):

    data_str = source_node.userData(
        TkFileNodeHandler.TK_OUTPUT_CONNECTIONS_KEY)

    if not data_str:
        return

    # parse the data str to determine the codec used
    sep_index = data_str.find(":")
    codec_name = data_str[:sep_index]
    data_str = data_str[sep_index + 1:]

    # get the matching decoder based on the codec name
    handler_cls = TkFileNodeHandler
    codecs = handler_cls.TK_OUTPUT_CONNECTION_CODECS
    decoder = codecs[codec_name]['decode']

    # decode the data str back into original python objects
    outputs = decoder(data_str)

    if not outputs:
        return

    for connection in outputs:
        output_node = hou.node(connection['node'])
        output_node.setInput(connection['input'], target_node)

