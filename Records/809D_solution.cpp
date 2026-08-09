#include <bits/stdc++.h>

using namespace std;

#define MAX_NODES (300000 + 10)

struct Treap_Node {
    int value, priority, left, right, lazy_add_tag;
};

Treap_Node Nodes[MAX_NODES];
int next_node_id, root_treap_id;

mt19937 random_generator(time(0) + clock());

int CreateNode(int val) {
    int id = next_node_id;
    next_node_id = next_node_id + 1;
    Nodes[id].value = val;
    Nodes[id].priority = random_generator();
    Nodes[id].left = 0;
    Nodes[id].right = 0;
    Nodes[id].lazy_add_tag = 0;
    return id;
}

void ApplyLazy(int node_id, int amount) {
    if (node_id != 0) {
        Nodes[node_id].value = Nodes[node_id].value + amount;
        Nodes[node_id].lazy_add_tag = Nodes[node_id].lazy_add_tag + amount;
    }
}

void PushDownLazy(int node_id) {
    if (node_id != 0 && Nodes[node_id].lazy_add_tag != 0) {
        ApplyLazy(Nodes[node_id].left, Nodes[node_id].lazy_add_tag);
        ApplyLazy(Nodes[node_id].right, Nodes[node_id].lazy_add_tag);
        Nodes[node_id].lazy_add_tag = 0;
    }
}

void Split(int u_id, int w, int &x_id, int &y_id) {
    if (u_id == 0) {
        x_id = 0;
        y_id = 0;
        return;
    }

    PushDownLazy(u_id);
    if (Nodes[u_id].value > w) {
        Split(Nodes[u_id].left, w, x_id, Nodes[u_id].left);
        y_id = u_id;
    } else {
        Split(Nodes[u_id].right, w, Nodes[u_id].right, y_id);
        x_id = u_id;
    }
}

int Merge(int u_id, int v_id) {
    if (u_id == 0) return v_id;
    if (v_id == 0) return u_id;

    PushDownLazy(u_id);
    PushDownLazy(v_id);

    if (Nodes[u_id].priority < Nodes[v_id].priority) {
        Nodes[u_id].right = Merge(Nodes[u_id].right, v_id);
        return u_id;
    } else {
        Nodes[v_id].left = Merge(u_id, Nodes[v_id].left);
        return v_id;
    }
}

int GetFront(int u_id) {
    if (u_id == 0) return INT_MAX; // Should not happen with initial 0 node
    if (Nodes[u_id].left == 0) return Nodes[u_id].value;
    PushDownLazy(u_id);
    return GetFront(Nodes[u_id].left);
}

void InsertIntoTreap(int &rt_id_ref, int x) {
    int new_node_id = CreateNode(x);
    rt_id_ref = Merge(rt_id_ref, new_node_id);
}

void EraseFrontFromTreap(int &rt_id_ref) {
    if (rt_id_ref == 0) return;

    int val_to_remove = GetFront(rt_id_ref);
    int a_id, b_id; // IDs for split results
    Split(rt_id_ref, val_to_remove, a_id, b_id); // 'a_id' will root the subtree of nodes with value <= val_to_remove

    // To remove the node with `val_to_remove` (which is the root of `a_id` if unique),
    // we merge its children with the `b_id` part.
    rt_id_ref = Merge(Nodes[a_id].left, Merge(Nodes[a_id].right, b_id));
}

void UpdateTreap(int l, int r) {
    int a_id, b_id, c_id, d_id; // IDs for sub-treaps after splits

    // Step 1: Split the `root_treap_id` by `l-1`. 
    // `a_id` will contain nodes with values < `l`. These represent LIS endings that can be extended by picking `l`.
    // `b_id` will contain nodes with values >= `l`.
    Split(root_treap_id, l - 1, a_id, b_id);

    // Step 2: Insert `l` as a new candidate LIS ending value into `a_id`. 
    // This models the case where an LIS ending at `v < l` can be extended by `l`.
    InsertIntoTreap(a_id, l);

    // Step 3: Split `b_id` by `r-1`.
    // `c_id` will contain nodes with values in `[l, r-1]`. These LIS endings `v` can be extended by picking `v+1`.
    // `d_id` will contain nodes with values >= `r`. These LIS endings `v` cannot be extended by `v+1` within `[l, r]`.
    Split(b_id, r - 1, c_id, d_id);

    // Step 4: Increment all values in `c_id` by 1 (lazy propagation).
    // This models `dp[k]` becoming `dp[k-1]+1` for relevant lengths `k`.
    ApplyLazy(c_id, 1);

    // Step 5: Remove the smallest value from `d_id`.
    // This prunes values `>= r` that become suboptimal or unextendable by `v+1` given the current interval.
    EraseFrontFromTreap(d_id);

    // Step 6: Merge the resulting Treap parts back together in order: `a_id`, then `c_id`, then `d_id`.
    root_treap_id = Merge(a_id, Merge(c_id, d_id));
}

int GetTreapSize(int u_id) {
    if (u_id == 0) return 0;
    PushDownLazy(u_id); // Important to push down lazy tags if value affects structure for any reason, though not strictly needed for size
    return GetTreapSize(Nodes[u_id].left) + GetTreapSize(Nodes[u_id].right) + 1;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int N;
    cin >> N;

    next_node_id = 1; // Node IDs start from 1
    root_treap_id = CreateNode(0); // Initialize Treap with a dummy node representing LIS length 0, ending at day 0.

    for (int i = 0; i < N; i++) {
        int l, r;
        cin >> l >> r;
        UpdateTreap(l, r);
    }

    // The final maximal LIS length is the total number of nodes in the Treap, minus the initial dummy '0' node.
    cout << GetTreapSize(root_treap_id) - 1 << endl;

    return 0;
}