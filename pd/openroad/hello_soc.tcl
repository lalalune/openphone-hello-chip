set script_dir [file dirname [file normalize [info script]]]
set repo_dir [file normalize "$script_dir/../.."]

read_verilog "$repo_dir/build/netlist/hello_chip_synth.v"
link_design hello_chip_top
read_sdc "$repo_dir/pd/constraints/hello_soc.sdc"
report_checks
report_wns
report_tns
