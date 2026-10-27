use std::io::{self, Read};

fn main() {
    let mut bytes = Vec::new();
    io::stdin().read_to_end(&mut bytes).unwrap();
    for byte in bytes {
        print!("{byte:02x}");
    }
    println!();
}
