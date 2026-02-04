function kstg --description "k wrapper for stg cluster"
    set -lx KUBECONFIG ~/Work/configurations/stg-main-cluster.yml
    k $argv
end
