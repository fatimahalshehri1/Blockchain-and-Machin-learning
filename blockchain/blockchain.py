import datetime as dt
import hashlib
import json
# type: ignore
import magic
from urllib.parse import urlparse
from fastapi import FastAPI, UploadFile, File, HTTPException
import os

app = FastAPI()


class Blockchain:
    def __init__(self):
        self.chain = []
        self.nodes = set()
        initial_block = self._create_block(
            data="genesis block", proof=1, previous_hash="0", index=1, file_path=None, is_ransomware=False  # type: ignore
        )
        self.chain.append(initial_block)


    def mine_block(self, data: str) -> dict:
        previous_block = self.get_previous_block()
        previous_proof = previous_block["proof"]
        index = len(self.chain) + 1
        proof = self._proof_of_work(
            previous_proof=previous_proof, index=index, data=data
        )
        previous_hash = self._hash(block=previous_block)
        block = self._create_block(
            data=data, proof=proof, previous_hash=previous_hash, index=index, file_path=None, is_ransomware=False  # type: ignore
        )
        self.chain.append(block)
        return block

    def mine_file_block(self, file_path: str) -> dict:
        file_type = magic.from_file(file_path, mime=True)
        if "text" in file_type:
            with open(file_path, 'rb') as f:
                file_contents = f.read()
                data = os.path.basename(file_path)
                index = len(self.chain) + 1
                previous_block = self.get_previous_block()
                previous_proof = previous_block["proof"]
                proof = self._proof_of_work(
                    previous_proof=previous_proof, index=index, data=data
                )
                previous_hash = self._hash(block=previous_block)
                is_ransomware = self._detect_ransomware(file_contents)  # type: ignore

                if is_ransomware:
                    # File contains ransomware, do not add to blockchain
                    return None  # type: ignore

                block = self._create_block(data=data, proof=proof, previous_hash=previous_hash,
                                           index=index, file_path=file_path, is_ransomware=is_ransomware)
                self.chain.append(block)
                return block
        else:
            return None  # type: ignore

    def _create_block(
        self, data: str, proof: int, previous_hash: str, index: int, file_path: str, is_ransomware: bool = False
    ) -> dict:
        block = {
            "index": index,
            "timestamp": str(dt.datetime.now()),
            "data": data,
            "proof": proof,
            "previous_hash": previous_hash,
        }

        if file_path is not None:
            with open(file_path, 'rb') as f:
                file_contents = f.read()
                block['file_contents'] = str(file_contents)

        if is_ransomware:
            block['is_ransomware'] = is_ransomware

        return block

    def get_previous_block(self) -> dict:
        return self.chain[-1]

    def _to_digest(
        self, new_proof: int, previous_proof: int, index: int, data: str
    ) -> bytes:
        to_digest = str(new_proof ** 2 - previous_proof ** 2 + index) + data
        return to_digest.encode()

    def _proof_of_work(self, previous_proof: str, index: int, data: str) -> int:
        new_proof = 1
        check_proof = False

        while not check_proof:
            to_digest = self._to_digest(new_proof, previous_proof, index, data)  # type: ignore
            hash_operation = hashlib.sha256(to_digest).hexdigest()
            if hash_operation[:4] == "0000":
                check_proof = True
            else:
                new_proof += 1

        return new_proof

    def _hash(self, block: dict) -> str:
        encoded_block = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(encoded_block).hexdigest()

    def is_chain_valid(self) -> bool:
        previous_block = self.chain[0]
        block_index = 1

        while block_index < len(self.chain):
            block = self.chain[block_index]
            if block["previous_hash"] != self._hash(previous_block):
                return False

            previous_proof = previous_block["proof"]
            index, data, proof = block["index"], block["data"], block["proof"]
            hash_operation = hashlib.sha256(
                self._to_digest(
                    new_proof=proof,
                    previous_proof=previous_proof,
                    index=index,
                    data=data,
                )
            ).hexdigest()

            if hash_operation[:4] != "0000":
                return False

            previous_block = block
            block_index += 1

        return True

    def calculate_file_hash(self, file_path):
        with open(file_path, "rb") as f:
            file_content = f.read()
        return hashlib.sha256(file_content).hexdigest()

    def get_chain(self) -> list[dict]:
        return self.chain

    def add_block(self, block: dict) -> None:
        self.chain.append(block)
