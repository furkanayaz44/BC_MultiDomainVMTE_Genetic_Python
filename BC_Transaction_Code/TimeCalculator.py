import random

class TimeCalculator:
    def __init__(self):

        # Initialize TimeCalculator
        # double min_proc_h = 1, min_proc_s = 1, min_proc_c = 1, min_prop_c_c = 28, min_prop_s_c = 4, min_prop_h_s = 2,
        #		min_comp_local_path = 2, min_comp_path_e2e_controller = 2, min_comp_path_e2e_broker = 8,
        #		max_proc_h = 1, max_proc_s = 1, max_proc_c = 1, max_prop_c_c = 32, max_prop_s_c = 6, max_prop_h_s = 2,
        #		max_comp_local_path = 4, max_comp_path_e2e_controller = 4, max_comp_path_e2e_broker = 12;
        # Initialize min and max values
        self.min_proc_h = 1
        self.min_proc_s = 1
        self.min_proc_c = 1
        self.min_prop_c_c = 28
        self.min_prop_s_c = 4
        self.min_prop_h_s = 2
        self.min_comp_local_path = 2
        self.min_comp_path_e2e_controller = 2
        self.min_comp_path_e2e_broker = 8

        self.max_proc_h = 1
        self.max_proc_s = 1
        self.max_proc_c = 1
        self.max_prop_c_c = 32
        self.max_prop_s_c = 6
        self.max_prop_h_s = 2
        self.max_comp_local_path = 4
        self.max_comp_path_e2e_controller = 4
        self.max_comp_path_e2e_broker = 12

    def get_fs_rc(self, path):
        result = self._get_rnd_value(self.min_proc_h, self.max_proc_h)
        result += self._get_rnd_value(self.min_prop_h_s, self.max_prop_h_s)
        result += self._get_rnd_value(self.min_proc_s, self.max_proc_s)
        result += self._get_rnd_value(self.min_prop_s_c, self.max_prop_s_c)
        result += self._get_rnd_value(self.min_proc_c, self.max_proc_c)
        result += path
        result += sum([
            self._get_rnd_value(self.min_prop_c_c, self.max_prop_c_c),
            self._get_rnd_value(self.min_proc_c, self.max_proc_c),
            self._get_rnd_value(self.min_proc_c, self.max_proc_c),
            self._get_rnd_value(self.min_prop_c_c, self.max_prop_c_c),
            self._get_rnd_value(self.min_prop_s_c, self.max_prop_s_c),
            self._get_rnd_value(self.min_proc_c, self.max_proc_c)
        ])
        result += sum([
            self._get_rnd_value(self.min_prop_s_c, self.max_prop_s_c),
            self._get_rnd_value(self.min_proc_s, self.max_proc_s),
            self._get_rnd_value(self.min_prop_h_s, self.max_prop_h_s),
            self._get_rnd_value(self.min_proc_h, self.max_proc_h)
        ])
        return result

    # path = measured time for path finding process in the algorithm
    def get_fs_od(self, path):
        result = self._get_rnd_value(self.min_proc_h, self.max_proc_h)
        result += self._get_rnd_value(self.min_prop_h_s, self.max_prop_h_s)
        result += self._get_rnd_value(self.min_proc_s, self.max_proc_s)
        result += self._get_rnd_value(self.min_proc_s, self.max_proc_s)
        result += self._get_rnd_value(self.min_prop_s_c, self.max_prop_s_c)
        result += self._get_rnd_value(self.min_proc_c, self.max_proc_c)
        result += self._get_rnd_value(self.min_prop_c_c, self.max_prop_c_c)
        result += max(
            self._get_rnd_value(self.min_prop_c_c, self.max_prop_c_c) + path +
            self._get_rnd_value(self.min_prop_c_c, self.max_prop_c_c),
            self._get_rnd_value(self.min_prop_c_c, self.max_prop_c_c) + path +
            self._get_rnd_value(self.min_prop_c_c, self.max_prop_c_c)
        )
        result += path
        result += sum([
            self._get_rnd_value(self.min_prop_c_c, self.max_prop_c_c),
            path,
            self._get_rnd_value(self.min_prop_c_c, self.max_prop_c_c),
            self._get_rnd_value(self.min_prop_s_c, self.max_prop_s_c),
            self._get_rnd_value(self.min_proc_c, self.max_proc_c)
        ])
        return result

    def get_fs_dcd(self, num_of_controller, path):
        result = self._get_rnd_value(self.min_proc_h, self.max_proc_h)
        result += self._get_rnd_value(self.min_prop_h_s, self.max_prop_h_s)
        result += self._get_rnd_value(self.min_proc_s, self.max_proc_s)
        result += self._get_rnd_value(self.min_proc_s, self.max_proc_s)
        result += self._get_rnd_value(self.min_prop_s_c, self.max_prop_s_c)
        result += self._get_rnd_value(self.min_proc_c, self.max_proc_c)
        result += num_of_controller * path + (num_of_controller - 1) * self._get_rnd_value(self.min_prop_c_c, self.max_prop_c_c)
        result += max(
            self._get_rnd_value(self.min_proc_c, self.max_proc_c),
            self._get_rnd_value(self.min_prop_s_c, self.max_prop_s_c)
        )
        return result

    def get_mep_rc(self, num_of_as, num_of_node):
        return 2 * num_of_as + num_of_node

    def get_mep_od(self, num_of_as, num_of_node, num_of_edge_src, num_of_edge_dest):
        return 4 + num_of_edge_src + num_of_edge_dest + 2 * num_of_as + num_of_node

    def get_mep_dcd(self, num_of_as, num_of_node):
        return 1 + 2 * num_of_as + num_of_node

    def get_mep_sc(self, num_of_as, num_of_node):
        return num_of_as + num_of_node

    def _get_rnd_value(self, min_val, max_val):
        return random.uniform(min_val, max_val)
