# Copyright (c) 2015 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
File Output node App for use with Toolkit's Houdini engine.
"""

import sgtk


class TkFileNodeApp(sgtk.platform.Application):
    """The file Output Node."""

    def init_app(self):
        """Initialize the app."""

        tk_houdini_file = self.import_module("tk_houdini_filenode")
        self.handler = tk_houdini_file.TkFileNodeHandler(self)

    def convert_to_regular_file_nodes(self):
        """Convert Toolkit file nodes to regular file nodes.
        
        Convert all Toolkit file nodes found in the current script to
        regular file nodes. Additional Toolkit information will be stored in
        user data named 'tk_*'

        Example usage::

        >>> import sgtk
        >>> eng = sgtk.platform.current_engine()
        >>> app = eng.apps["tk-houdini-filenode"]
        >>> app.convert_to_regular_file_nodes()

        """

        self.log_debug(
            "Converting Toolkit file nodes to built-in file nodes.")
        tk_houdini_file = self.import_module("tk_houdini_filenode")
        tk_houdini_file.TkFileNodeHandler.\
            convert_to_regular_file_nodes(self)

    def convert_back_to_tk_file_nodes(self):
        """Convert regular file nodes back to Tooklit file nodes.
        
        Convert any regular file nodes that were previously converted
        from Tooklit file nodes back into Toolkit file nodes.

        Example usage::

        >>> import sgtk
        >>> eng = sgtk.platform.current_engine()
        >>> app = eng.apps["tk-houdini-filenode"]
        >>> app.convert_back_to_tk_file_nodes()

        """

        self.log_debug(
            "Converting built-in File nodes back to Toolkit File nodes.")
        tk_houdini_file = self.import_module("tk_houdini_filenode")
        tk_houdini_file.TkFileNodeHandler.\
            convert_back_to_tk_file_nodes(self)

    def get_nodes(self):
        """
        Returns a list of hou.node objects for each tk file node.

        Example usage::

        >>> import sgtk
        >>> eng = sgtk.platform.current_engine()
        >>> app = eng.apps["tk-houdini-filenode"]
        >>> tk_file_nodes = app.get_nodes()
        """

        self.log_debug("Retrieving tk-houdini-file nodes...")
        tk_houdini_file = self.import_module("tk_houdini_filenode")
        nodes = tk_houdini_file.TkFileNodeHandler.\
            get_all_tk_file_nodes()
        self.log_debug("Found %s tk-houdini-file nodes." % (len(nodes),))
        return nodes

    def get_output_path(self, node):
        """
        Returns the evaluated output path for the supplied node.

        Example usage::

        >>> import sgtk
        >>> eng = sgtk.platform.current_engine()
        >>> app = eng.apps["tk-houdini-filenode"]
        >>> output_path = app.get_output_path(tk_file_node)
        """

        self.log_debug("Retrieving output path for %s" % (node,))
        tk_houdini_file = self.import_module("tk_houdini_filenode")
        output_path = tk_houdini_file.TkFileNodeHandler.\
            get_output_path(node)
        self.log_debug("Retrieved output path: %s" % (output_path,))
        return output_path
