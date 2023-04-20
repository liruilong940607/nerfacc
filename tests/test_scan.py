import pytest
import torch

device = "cuda:0"


@pytest.mark.skipif(not torch.cuda.is_available, reason="No CUDA device")
def test_inclusive_sum():
    from nerfacc.scan import inclusive_sum

    torch.manual_seed(42)

    data = torch.rand((5, 1000), device=device, requires_grad=True)
    outputs1 = inclusive_sum(data)
    outputs1.sum().backward()
    grad1 = data.grad.clone()
    data.grad.zero_()

    data_csr = data.to_sparse_csr()
    crow_indices = data_csr.crow_indices().detach()
    data2 = data_csr.values().detach()
    data2.requires_grad = True

    outputs2 = inclusive_sum(data2, crow_indices)
    outputs2.sum().backward()
    grad2 = data2.grad.clone()
    data2.grad.zero_()

    assert torch.allclose(outputs1.flatten(), outputs2)
    assert torch.allclose(grad1.flatten(), grad2)


@pytest.mark.skipif(not torch.cuda.is_available, reason="No CUDA device")
def test_exclusive_sum():
    from nerfacc.scan import exclusive_sum

    torch.manual_seed(42)

    data = torch.rand((5, 1000), device=device, requires_grad=True)
    outputs1 = exclusive_sum(data)
    outputs1.sum().backward()
    grad1 = data.grad.clone()
    data.grad.zero_()

    data_csr = data.to_sparse_csr()
    crow_indices = data_csr.crow_indices().detach()
    data2 = data_csr.values().detach()
    data2.requires_grad = True

    outputs2 = exclusive_sum(data2, crow_indices)
    outputs2.sum().backward()
    grad2 = data2.grad.clone()
    data2.grad.zero_()

    assert torch.allclose(outputs1.flatten(), outputs2)
    assert torch.allclose(grad1.flatten(), grad2)


@pytest.mark.skipif(not torch.cuda.is_available, reason="No CUDA device")
def test_inclusive_prod():
    from nerfacc.scan import inclusive_prod

    torch.manual_seed(42)

    data = torch.rand((5, 1000), device=device, requires_grad=True)
    outputs1 = inclusive_prod(data)
    outputs1.sum().backward()
    grad1 = data.grad.clone()
    data.grad.zero_()

    data_csr = data.to_sparse_csr()
    crow_indices = data_csr.crow_indices().detach()
    data2 = data_csr.values().detach()
    data2.requires_grad = True

    outputs2 = inclusive_prod(data2, crow_indices)
    outputs2.sum().backward()
    grad2 = data2.grad.clone()
    data2.grad.zero_()

    assert torch.allclose(outputs1.flatten(), outputs2)
    assert torch.allclose(grad1.flatten(), grad2)


@pytest.mark.skipif(not torch.cuda.is_available, reason="No CUDA device")
def test_exclusive_prod():
    from nerfacc.scan import exclusive_prod

    torch.manual_seed(42)

    data = torch.rand((5, 1000), device=device, requires_grad=True)
    outputs1 = exclusive_prod(data)
    outputs1.sum().backward()
    grad1 = data.grad.clone()
    data.grad.zero_()

    data_csr = data.to_sparse_csr()
    crow_indices = data_csr.crow_indices().detach()
    data2 = data_csr.values().detach()
    data2.requires_grad = True

    outputs2 = exclusive_prod(data2, crow_indices)
    outputs2.sum().backward()
    grad2 = data2.grad.clone()
    data2.grad.zero_()

    # TODO: check exclusive sum. numeric error?
    # print((outputs1 - outputs2).abs().max())
    assert torch.allclose(outputs1.flatten(), outputs2)
    assert torch.allclose(grad1.flatten(), grad2)


if __name__ == "__main__":
    test_inclusive_sum()
    test_exclusive_sum()
    test_inclusive_prod()
    test_exclusive_prod()
